from math import floor

from numpy import double
from SPN.Token import Token
from SPN.State import State
from Shared.Enums import Type
from Shared.Enums import Phase
from queue import PriorityQueue
from random import choices, randint
import copy

class SPN:
    def __init__(self, glossaList, startTime, endTime):
        # Current busy agents/patients
        self.busyAgents = []
        self.busyPatients = []
        # All agent and patient busy times
        self.apBusyTimes = {}
        #The current state of the agents/patients
        self.apStates = {}
        # Token/State starting ID
        self.id = 0
        # State machine
        self.stateMachine = PriorityQueue()
        # Current time
        self.time = 0
        # State machine start and end time
        self.startTime = startTime
        self.endTime = endTime
        self.lastEndTime = startTime
        self.previousTiming = -10
        # order the glossa by timing
        glossaOrderTimes = [(min(kernelList), i) for i, kernelList in enumerate(glossaList.kernelList)]
        glossaOrderTimes = sorted(glossaOrderTimes)
        while len(glossaOrderTimes) > 0:
            # Get next glossa
            g = glossaOrderTimes.pop(0)
            index = g[1]
            timing = g[0].timing
            allGlossa = []
            glossaWithSeps = glossaList.glossa[index]
            allGlossa.append(glossaWithSeps)
            # Determine if two sentencce glossas have the same timing, if so combine them
            if len(glossaOrderTimes) > 0 and all(kernel.timing == timing for kernel in glossaList.kernelList[index]):
                if index < len(glossaList.kernelList) - 1 and all(kernel.timing == timing for kernel in glossaList.kernelList[index + 1]):
                    allGlossa.append(glossaList.glossa[index + 1])
                    glossaOrderTimes.remove((min(glossaList.kernelList[index + 1]), index + 1))
                elif index > 0 and all(kernel.timing == timing for kernel in glossaList.kernelList[index - 1]):
                    allGlossa.append(glossaList.glossa[index - 1])
                    glossaOrderTimes.remove((min(glossaList.kernelList[index - 1]), index + 1))
                if len(allGlossa) > 1:
                    newGlossa = []
                    newGlossa.append(allGlossa[0])
                    newGlossa.append("#!")
                    newGlossa.append(allGlossa[1])
                    glossaWithSeps = newGlossa
            # Get all of the times of each kernel in the sentence
            allTimes = []
            for kernel in glossaList.kernelList[index]:
                time = kernel.timing
                if time not in allTimes:
                    allTimes.append(time)
            allTimes.sort()
            # For each kernel time
            for time in allTimes:
                # Determine the agent, action, and patient combinations of kernels with the same time
                kernels = self.GetInitialKernelCombinations(0, len(glossaWithSeps), glossaWithSeps, time)
                # Pick a random agent, action, and patient combination
                if type(kernels) is not list:
                    kernelState = [kernels]
                elif any(type(x) is list for x in kernels):
                        self.PrintKernelChoices(kernels, glossaList.agentList, glossaList.actionList, glossaList.patientList)
                        probabilitiesString = input("Please enter a probability for each option (seperated by a space): ")
                        probabilitiesList = probabilitiesString.split(" ")
                        probabilitiesList = [double(probability) for probability in probabilitiesList]
                        index = choices(range(0, len(kernels)), weights = probabilitiesList, k = 1)
                        kernelState = kernels[index[0]]
                else:
                    kernelState = kernels
                # Consolidate all of the agents, actions, and patients of the kernel combination
                allAgents = []
                allPatients = []
                for kernel in kernelState:
                    for agents in kernel[0]:
                        if len(agents) == 1:
                            allAgents.append(agents[0])
                        else:
                            allAgents.extend(agents)
                    for patients in kernel[2]:
                        if len(patients) == 1:
                            allPatients.append(patients[0])
                        else:
                            allPatients.extend(patients)
                allAgents = list(set(allAgents))
                allPatients = list(set(allPatients))
                for agent in allAgents:
                    if agent not in self.apStates:
                        self.apStates[agent] = agent
                        self.apBusyTimes[agent] = []
                for patient in allPatients:
                    if patient not in self.apStates:
                        self.apStates[patient] = patient
                        self.apBusyTimes[patient] = []
                self.UpdateBusyTimesNew(allAgents, allPatients, glossaList.agentList, glossaList.patientList)
                # Determine first transition time (pre action entry which is the same for all kernels)
                allBusyTimes = self.GetAllBusyTimes(allAgents, allPatients, glossaList.agentList, glossaList.patientList)
                allBusyTimes.sort()
                if time == self.previousTiming + 1 or time == self.previousTiming - 1:
                    transTime1 = self.GetFirstTransitionTime(allBusyTimes, self.lastEndTime)
                else:
                    transTime1 = self.GetFirstTransitionTime(allBusyTimes, self.startTime)
                for kernel in kernelState:
                    # Select random agents, actions, and patients for each individual kernel
                    allKernelAgents = [j for i in kernel[0] for j in i]
                    allKernelPatients = [j for i in kernel[2] for j in i]
                    allKernelAgents = list(set(allKernelAgents))
                    allKernelPatients = list(set(allKernelPatients))
                    # There are no agents
                    if len(kernel[0]) == 0:
                        randomAgents = []
                        otherAgents = []
                    # There is only one agent
                    elif len(kernel[0]) == 1:
                        randomAgents = kernel[0][0]
                        otherAgents = []
                    # The user must select an agent
                    else:
                        self.PrintAVPChoices(kernel[0], glossaList.agentList, Type.Agent)
                        probabilitiesString = input("Please enter a probability for each option (seperated by a space): ")
                        probabilitiesList = probabilitiesString.split(" ")
                        probabilitiesList = [double(probability) for probability in probabilitiesList]
                        index = choices(range(0, len(kernel[0])), weights = probabilitiesList, k = 1)
                        randomAgents = kernel[0][index[0]]
                        otherAgents = [i for i in allKernelAgents if i not in randomAgents]
                    # There is only one action
                    if len(kernel[1]) == 1:
                        randomActions = kernel[1][0]
                    # The user must select an action
                    else:
                        self.PrintAVPChoices(kernel[1], glossaList.actionList, Type.Action)
                        probabilitiesString = input("Please enter a probability for each option (seperated by a space): ")
                        probabilitiesList = probabilitiesString.split(" ")
                        probabilitiesList = [double(probability) for probability in probabilitiesList]
                        index = choices(range(0, len(kernel[1])), weights = probabilitiesList, k = 1)
                        randomActions = kernel[1][index[0]]
                    # There are no patients
                    if len(kernel[2]) == 0:
                        randomPatients = []
                        otherPatients = []
                    # There is only one patient
                    elif len(kernel[2]) == 1:
                        randomPatients = kernel[2][0]
                        otherPatients = []
                    # The user must select a patient
                    else:
                        self.PrintAVPChoices(kernel[2], glossaList.patientList, Type.Patient)
                        probabilitiesString = input("Please enter a probability for each option (seperated by a space): ")
                        probabilitiesList = probabilitiesString.split(" ")
                        probabilitiesList = [double(probability) for probability in probabilitiesList]
                        index = choices(range(0, len(kernel[2])), weights = probabilitiesList, k = 1)
                        randomPatients = kernel[2][index[0]]
                        otherPatients = [i for i in allKernelPatients if i not in randomPatients]
                    allBusyTimes = self.GetAllBusyTimes(allKernelAgents, allKernelPatients, glossaList.agentList, glossaList.patientList)
                    nextBusyTime = self.GetNextBusyTime(allBusyTimes, transTime1)
                    # Select random transition times for each individual kernel
                    transTime2 = self.GetSecondTransitionTime(transTime1, nextBusyTime)
                    transTime3 = self.GetThirdTransitionTime(transTime2, nextBusyTime)
                    # Extend end time if necessary
                    self.lastEndTime = transTime3
                    if self.endTime - self.lastEndTime < 10:
                        self.endTime += 100
                    transitionTimes = [transTime1, transTime2, transTime3]
                    # Save last time
                    self.previousTiming = time
                    # Add the transition times to the busy times of agents and patients
                    self.UpdateBusyTimes(randomAgents, otherAgents, randomPatients, otherPatients, transitionTimes, glossaList.agentList, glossaList.patientList)
                    # Create new token for kernel
                    t = Token(self.id, 0, transitionTimes, randomActions, randomAgents, otherAgents, randomPatients, otherPatients)
                    self.id += 1
                    self.stateMachine.put((t.releaseTime, t))

    def PrintKernelChoices(self, kernelOptions, agentList, actionList, patientList):
        # Print user kernel options
        print("Kernel Options: ")
        for i, kernelOption in enumerate(kernelOptions):
            printOptionList = []
            for kernel in kernelOption:
                printAgents = []
                for kernelAgents in kernel[0]:
                    agentIndicies = [int(agent[1]) for agent in kernelAgents]
                    printAgents.append([agentList[agent] for agent in agentIndicies])
                    printAgents.append(" or ")
                printActions = []
                for kernelActions in kernel[1]:
                    actionIndicies = [int(action[1]) for action in kernelActions]
                    printActions.append([actionList[action] for action in actionIndicies])
                    printActions.append(" or ")
                printPatients = []
                for kernelPatients in kernel[2]:
                    patientIndicies = [int(patient[1]) for patient in kernelPatients]
                    printPatients.append([patientList[patient] for patient in patientIndicies])
                    printPatients.append(" or ")
                printAgents.pop(-1)
                printActions.pop(-1)
                printPatients.pop(-1)
                printOptionList.append(str(printAgents) + " -> " + str(printActions) + " -> " + str(printPatients))
                printOptionList.append("and")
            printOptionList.pop(-1)
            print("Option " + str(i + 1) + ": " + str(printOptionList))

    def PrintAVPChoices(self, options, typeList, type):
        # Print user AVP options
        if type == Type.Agent:
            print("Agent Options: ")
        elif type == Type.Action:
            print("Action Options: ")
        elif type == Type.Patient:
            print("Patient Options: ")
        for i, option in enumerate(options):
            itemIndicies = [int(item[1]) for item in option]
            printItems = [typeList[index] for index in itemIndicies]
            print("Option " + str(i + 1) + ": " + str(printItems))   

    def GetAllBusyTimes(self, allAgents, allPatients, agentList, patientList):
        # Determine when the specified agents and patients are busy
        allBusyTimes = []
        for agent in allAgents:
            allBusyTimes.extend(self.apBusyTimes[agent])
            agentName = agentList[int(agent[1])]
            if agentName in patientList:
                index = patientList.index(agentName)
                patientString = ''.join(['P', str(index)])
                if patientString in self.apBusyTimes:
                    allBusyTimes.extend(self.apBusyTimes[patientString])
        for patient in allPatients:
            allBusyTimes.extend(self.apBusyTimes[patient])
            patientName = patientList[int(patient[1])]
            if patientName in agentList:
                index = agentList.index(patientName)
                agentString = ''.join(['A', str(index)])
                if agentString in self.apBusyTimes:
                    allBusyTimes.extend(self.apBusyTimes[agentString])
        return list(set(allBusyTimes))

    def GetNextBusyTime(self, allBusyTimes, transTime1):
        # Determine the next time specified all agents and patients are busy after the pre aaction transition time
        t = 0
        while t < len(allBusyTimes) and allBusyTimes[t] <= transTime1:
            t += 1
        if t == len(allBusyTimes):
            return self.endTime
        return allBusyTimes[t]

    def GetFirstTransitionTime(self, allBusyTimes, start):
        # Determine first transition time, based on when the agents and patients are busy
        possibleT1Times = [t for t in range(start, self.endTime -  3) 
        if t not in allBusyTimes and t + 1 not in allBusyTimes and t + 2 not in allBusyTimes]
        return possibleT1Times[randint(0, len(possibleT1Times) - 1)]

    def GetSecondTransitionTime(self, transTime1, nextBusyTime):
        # Determine second transition time, based on when the agents and patients are busy next
        return randint(transTime1 + 1, nextBusyTime - 1)

    def GetThirdTransitionTime(self, transTime2, nextBusyTime):
        # Determine third transition time, based on when the agents and patients are busy next
        return randint(transTime2 + 1, nextBusyTime)

    def UpdateBusyTimesNew(self, allAgents, allPatients, agentList, patientList):
        # Copy over busy times to new agents or patients, that were patients or agents already
        for agent in allAgents:
            agentName = agentList[int(agent[1])]
            if agentName in patientList:
                index = patientList.index(agentName)
                patientString = ''.join(['P', str(index)])
                if patientString in self.apBusyTimes:
                    self.apBusyTimes[agent].extend(self.apBusyTimes[patientString])  
        for patient in allPatients:
            patientName = patientList[int(patient[1])]
            if patientName in agentList:
                index = agentList.index(patientName)
                agentString = ''.join(['A', str(index)])
                if agentString in self.apBusyTimes:
                    self.apBusyTimes[patient].extend(self.apBusyTimes[agentString])

    def UpdateBusyTimes(self, randomAgents, otherAgents, randomPatients, otherPatients, transitionTimes, agentList, patientList):
        # Update the times when the agents and patents are busy based on new transition times
        selectedBusyTimes = [i for i in range (transitionTimes[0], transitionTimes[2] + 2)]
        for agent in randomAgents:
            self.apBusyTimes[agent].extend(selectedBusyTimes)
            agentName = agentList[int(agent[1])]
            if agentName in patientList:
                index = patientList.index(agentName)
                patientString = ''.join(['P', str(index)])
                if patientString in self.apBusyTimes:
                    self.apBusyTimes[patientString].extend(selectedBusyTimes)
        otherBusyTimes = [i for i in range (transitionTimes[0], transitionTimes[1] + 2)]  
        for agent in otherAgents:
            self.apBusyTimes[agent].extend(otherBusyTimes)
            agentName = agentList[int(agent[1])]
            if agentName in patientList:
                index = patientList.index(agentName)
                patientString = ''.join(['P', str(index)])
                if patientString in self.apBusyTimes:
                    self.apBusyTimes[patientString].extend(otherBusyTimes)  
        for patient in randomPatients:
            self.apBusyTimes[patient].extend(selectedBusyTimes)
            patientName = patientList[int(patient[1])]
            if patientName in agentList:
                index = agentList.index(patientName)
                agentString = ''.join(['A', str(index)])
                if agentString in self.apBusyTimes:
                    self.apBusyTimes[agentString].extend(selectedBusyTimes)
        for patient in otherPatients:
            self.apBusyTimes[patient].extend(otherBusyTimes)
            patientName = patientList[int(patient[1])]
            if patientName in agentList:
                index = agentList.index(patientName)
                agentString = ''.join(['A', str(index)])
                if agentString in self.apBusyTimes:
                    self.apBusyTimes[agentString].extend(otherBusyTimes)

    def GetInitialAPVCombinations(self, start, end, glossa, type):
        # Determine kernel subtype (agent, action, or patient)
        if type == Type.Agent:
            operators = ["*", "%"]
        elif type == Type.Action:
            operators = ["^", "~"]
        elif type == Type.Patient:
            operators = ["@", "$"]
        if len(glossa) == 0:
            return glossa
        curGlossa = glossa[start:end]
        # If there is only one of a kerenel subtype
        if len(curGlossa) == 1 and isinstance(curGlossa[0], list):
            curGlossa = curGlossa[0]
            start = 0
            end = len(curGlossa)
            # If there are multiple operators, recursivly seperate them
        if any(isinstance(x, list) for x in curGlossa):
            middleIndex = floor(len(curGlossa) / 2)
            # AND operation gets seperated by commas
            if curGlossa[middleIndex] == operators[0]:
                l1 = self.GetInitialAPVCombinations(start, middleIndex, curGlossa, type) 
                l2 = self.GetInitialAPVCombinations(middleIndex + 1, end, curGlossa, type)
                # If OR proceeds and/or follows AND get all possible combinations for the subtype
                if any(isinstance(x, list) for x in l1) and any(isinstance(x, list) for x in l2):
                    l = []
                    for item1 in l1:
                        for item2 in l2:
                            tempItem = copy.deepcopy(item1)
                            tempItem.extend(item2)
                            l.append(tempItem)
                    return l
                elif any(isinstance(x, list) for x in l1):
                    l = []
                    for item1 in l1:
                        item1.extend(l2)
                        l.append(item1)
                    return l
                elif any(isinstance(x, list) for x in l2):
                    l = []
                    for item2 in l2:
                        item2.extend(l1)
                        l.append(item2)
                    return l
                else:
                    l1.extend(l2)
                    return l1 
            # OR operation gets seperated by lists
            if curGlossa[middleIndex] == operators[1]:
                l1 = self.GetInitialAPVCombinations(start, middleIndex, curGlossa, type)
                if isinstance(l1, list) and len(l1) == 1 and isinstance(l1[0], list) and len(l1[0]) > 1:
                    l1  = l1[0]
                l2 = self.GetInitialAPVCombinations(middleIndex + 1, end, curGlossa, type)
                if isinstance(l2, list) and len(l2) == 1 and isinstance(l2[0], list) and len(l2[0]) > 1:
                    l2 = l2[0]
                return [l1, l2]
        # If there is only one operator, seperate the kernel subtype accordingly
        elif len(curGlossa) > 1:
            if curGlossa[1] == operators[0]:
                a = curGlossa[::2]
                return [list(a)]
            elif curGlossa[1] == operators[1]:
                a = curGlossa[::2]
                return [[b] for b in a]
        else:
            return curGlossa

    def GetInitialKernelCombinations(self, start, end, glossa, time):
        operators = ["#", "!", "#!"]
        curGlossa = glossa[start:end]
        if len(curGlossa) == 1 and type(curGlossa[0]) is list:
            curGlossa = curGlossa[0]
        # if there is only one kernel
        if len(curGlossa) == 1:
            curKernel = curGlossa[0].kernel
            curGlossa = curGlossa[0].glossa
            start = 0
            end = len(curGlossa)
        if any(item == operators[2] for item in curGlossa):
            middleIndex = curGlossa.index(operators[2])
            l1 = self.GetInitialKernelCombinations(start, middleIndex, curGlossa, time)
            l2 = self.GetInitialKernelCombinations(middleIndex + 1, end, curGlossa, time)
            if isinstance(l1, tuple):
                l1 = [l1]
            if isinstance(l2, tuple):
                l2 = [l2]
            # If OR proceeds and/or follows AND get all possible combinations for the kernels
            if any(isinstance(x, list) for x in l1) and any(isinstance(x, list) for x in l2):
                l = []
                for item1 in l1:
                    for item2 in l2:
                        l.append([item1[0], item2[0]])
                return l
            elif any(isinstance(x, list) for x in l1):
                l = []
                for item1 in l1:
                    item1.extend(l2)
                    l.append(item1)
                return l
            elif any(isinstance(x, list) for x in l2):
                l = []
                for item2 in l2:
                    item2.extend(l1)
                    l.append(item2)
                return l
            else:
                l1.extend(l2)
                return l1 
        # If there are multiple kernels, recursivly seperate them
        if any(isinstance(x, list) for x in curGlossa):
            operatorIndecies = [(item, i) for i, item in enumerate(curGlossa) if item in operators]
            middleIndex = operatorIndecies[floor(len(operatorIndecies) / 2)][1]
            # AND operation gets seperated by commas
            if curGlossa[middleIndex] == operators[0]:
                l1 = self.GetInitialKernelCombinations(start, middleIndex, curGlossa, time) 
                l2 = self.GetInitialKernelCombinations(middleIndex + 1, end, curGlossa, time)
                # If OR proceeds and/or follows AND get all possible combinations for the kernels
                if any(isinstance(x, list) for x in l1) and any(isinstance(x, list) for x in l2):
                    l = []
                    for item1 in l1:
                        for item2 in l2:
                            l.append([item1[0], item2[0]])
                    return l
                elif any(isinstance(x, list) for x in l1):
                    l = []
                    for item1 in l1:
                        item1.extend(l2)
                        l.append(item1)
                    return l
                elif any(isinstance(x, list) for x in l2):
                    l = []
                    for item2 in l2:
                        item2.extend(l1)
                        l.append(item2)
                    return l
                else:
                    l1.extend(l2)
                    return l1 
            # OR operation gets seperated by lists
            elif curGlossa[middleIndex] == operators[1]:
                l1 = self.GetInitialKernelCombinations(start, middleIndex, curGlossa, time) 
                l2 = self.GetInitialKernelCombinations(middleIndex + 1, end, curGlossa, time)
                return [l1, l2]
        # If there is only one operator, seperate the kernels accordingly and only include the ones for the current time
        elif len(curGlossa) > 1 and any(isinstance(x, str) for x in curGlossa):
            if curGlossa[1] == operators[0]:
                glossaObjects = curGlossa[::2]
                allKernels = []
                for go in glossaObjects:
                    if go.kernel.timing == time:
                        glossa = go.glossa
                        stateAgents = self.GetInitialAPVCombinations(0, len(glossa[0]), glossa[0], Type.Agent)
                        agents = [item if isinstance(item, list) else [item] for item in stateAgents]
                        stateActions = self.GetInitialAPVCombinations(0, len(glossa[1]), glossa[1], Type.Action)
                        actions = [item if isinstance(item, list) else [item] for item in stateActions]
                        statePatients = self.GetInitialAPVCombinations(0, len(glossa[2]), glossa[2], Type.Patient)
                        patients = [item if isinstance(item, list) else [item] for item in statePatients]
                        allKernels.append((agents, actions, patients))
                return allKernels
            elif curGlossa[1] == operators[1]:
                glossaObjects = curGlossa[::2]
                allKernels = []
                for go in glossaObjects:
                    if go.kernel.timing == time:
                        glossa = go.glossa
                        stateAgents = self.GetInitialAPVCombinations(0, len(glossa[0]), glossa[0], Type.Agent)
                        agents = [item if isinstance(item, list) else [item] for item in stateAgents]
                        stateActions = self.GetInitialAPVCombinations(0, len(glossa[1]), glossa[1], Type.Action)
                        actions = [item if isinstance(item, list) else [item] for item in stateActions]
                        statePatients = self.GetInitialAPVCombinations(0, len(glossa[2]), glossa[2], Type.Patient)
                        patients = [item if isinstance(item, list) else [item] for item in statePatients]
                        allKernels.append([(agents, actions, patients)])
                return allKernels
        # If there is only one kernel, only include it if it is the current time
        else:
            if curKernel.timing == time:
                stateAgents = self.GetInitialAPVCombinations(0, len(curGlossa[0]), curGlossa[0], Type.Agent)
                agents = [item if isinstance(item, list) else [item] for item in stateAgents]
                stateActions = self.GetInitialAPVCombinations(0, len(curGlossa[1]), curGlossa[1], Type.Action)
                actions = [item if isinstance(item, list) else [item] for item in stateActions]
                statePatients = self.GetInitialAPVCombinations(0, len(curGlossa[2]), curGlossa[2], Type.Patient)
                patients = [item if isinstance(item, list) else [item] for item in statePatients]
                return (agents, actions, patients)
            else:
                return []
    

    def RunStateMachine(self, agentList, actionList, patientList):
        print()
        print(f"{'Time' : <10}{'State' : ^20}{'AVP' : ^30}")
        while not self.stateMachine.empty():
            item = self.stateMachine.get()
            self.time = item[0]
            if type(item[1]) is Token:
                # Add all 3 states to the state machine based on token information
                token = item[1]
                agentStates = [self.apStates[agent] for agent in token.affectedAgent]
                patientStates = [self.apStates[patient] for patient in token.affectedPatient]
                s1 = State(self.id, token.transitionTimes[0], token.action, Phase.PreAction, agentStates, patientStates, token.affectedAgent, token.otherAgent, token.affectedPatient, token.otherPatient)
                self.stateMachine.put((s1.transitionTime, s1))
                agentStates = [self.apStates[agent] + "'A" for agent in token.affectedAgent]
                patientStates = [self.apStates[patient] + "'A" for patient in token.affectedPatient]
                s2 = State(self.id, token.transitionTimes[1], token.action, Phase.Action, agentStates, patientStates, token.affectedAgent, token.otherAgent, token.affectedPatient, token.otherPatient)
                self.stateMachine.put((s2.transitionTime, s2))
                agentStates = [self.apStates[agent] +"'C" for agent in token.affectedAgent]
                patientStates = [self.apStates[patient] +"'C" for patient in token.affectedPatient]
                s3 = State(self.id, token.transitionTimes[2], token.action, Phase.PostAction, agentStates, patientStates, token.affectedAgent, token.otherAgent, token.affectedPatient, token.otherPatient)
                self.stateMachine.put((s3.transitionTime, s3))
            elif type(item[1]) is State:
                # Remove agents and patients from the busy list depending on the state type and print the current state
                state = item[1]
                for i, agent in enumerate(state.affectedAgent):
                        self.apStates[agent] = state.agentState[i]
                for i, patient in enumerate(state.affectedPatient):
                    self.apStates[patient] = state.patientState[i]
                state.PrintState(agentList, actionList, patientList, state.actionState)
                if state.actionState == Phase.PreAction:
                    for agent in state.affectedAgent:
                        if agent not in self.busyAgents:
                            self.busyAgents.append(agent)
                    for agent in state.otherAgent:
                        if agent not in self.busyAgents:
                            self.busyAgents.append(agent)
                    for patient in state.affectedPatient:
                        if patient not in self.busyPatients:
                            self.busyPatients.append(patient)
                    for patient in state.otherPatient:
                        if patient not in self.busyPatients:
                            self.busyPatients.append(patient)
                elif state.actionState == Phase.Action:
                    for agent in state.otherAgent:
                        if agent in self.busyAgents:
                            self.busyAgents.remove(agent)
                    for patient in state.otherPatient:
                        if patient in self.busyPatients:
                            self.busyPatients.remove(patient)
                elif state.actionState == Phase.PostAction:
                    for agent in state.affectedAgent:
                        if agent in self.busyAgents:
                            self.busyAgents.remove(agent)
                    for patient in state.affectedPatient:
                        if patient in self.busyPatients:
                            self.busyPatients.remove(patient)