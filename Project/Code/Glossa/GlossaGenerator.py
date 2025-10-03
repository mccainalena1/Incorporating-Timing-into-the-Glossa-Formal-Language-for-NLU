# Perform standard imports
from math import floor
import spacy
nlp = spacy.load('en_core_web_lg')
from Shared.Enums import Type
from Glossa.Glossa import Glossa

class GlossaGenerator:
    def __init__(self):
        # Glossa for a whole document
        self.glossa = []
        # Angents for a whole document
        self.agentList = []
        # Actions for a whole document
        self.actionList = []
        # Patients for a whole document
        self.patientList = []
        # Kernels for a whole document
        self.kernelList = []
    
    def AddSentenceToGlossa(self, kernels, kernelSeperators, kernelTimingBreak):
        for kernel in kernels:
            # Add new agents, actions, patients and kernels to glossa generatore
            for agent in kernel.agentStrings:
                if agent not in self.agentList:
                    self.agentList.append(agent)
        for kernel in kernels:
            for action in kernel.actionStrings:
                if action not in self.actionList:
                    self.actionList.append(action)
        for kernel in kernels:
            for patient in kernel.patientStrings:
                if patient not in self.patientList:
                    self.patientList.append(patient)
        self.kernelList.append(kernels)
        # Get glossa from kernels
        self.ConvertKernelsToGlossa(kernels, kernelSeperators, kernelTimingBreak)

    def ConvertKernelsToGlossa(self, kernels, kernelSeperators, kernelTimingBreak):
        ks = []
        # Get all of the actions, agents and patients from each kernel in the sentence
        for kernel in kernels:
            agents = self.GenerateKernelSectionGlossa(0, len(kernel.agent), kernel.agent, Type.Agent)
            actions = self.GenerateKernelSectionGlossa(0, len(kernel.action), kernel.action, Type.Action)
            patients = self.GenerateKernelSectionGlossa(0, len(kernel.patient), kernel.patient, Type.Patient)
            ks.append(Glossa(tuple([tuple(agents), tuple(actions), tuple(patients)]) , kernel))
        # Determine how the kernels are connected in the sentence
        kg = self.GenerateKernelGlossa(0, len(kernels[-1].sentence), ks, kernelSeperators, kernelTimingBreak)
        # Add sentence glossa to document glossa
        self.glossa.append(kg)

    def GenerateKernelSectionGlossa(self, start, end, typeList, type):
        # Determine kernel subtype (agent, action, or patient)
        if type == Type.Agent:
            operators = ["*", "%", "A"]
            typeStrings = self.agentList
        elif type == Type.Action:
            operators = ["^", "~", "V"]
            typeStrings = self.actionList
        elif type == Type.Patient:
            operators = ["@", "$", "P"]
            typeStrings = self.patientList
        glossaType = []
        # Find conjunctions and commas
        conjuntions = [i for i in range(start, end) if typeList[i].lower_ == "and" or typeList[i].lower_ == "or"]
        commas = [i for i in range(start, end) if typeList[i].text == ","]
        # If there is only one of the subtypes, get its glossa string
        if len(conjuntions) == 0:
            j = start
            name = ""
            while j < end:
                name += typeList[j].text + "_"
                j += 1
            if name != "":
                # Keep heyphens without underscores in nouns
                name = name.replace("_-_" ,"-")
                glossaType.append(''.join([operators[2], str(typeStrings.index(name[:-1]))]))
            return glossaType
        # if conjnction is between the subtypes, find all of ther glossa strings, seperated by the appropriate operator
        elif len(conjuntions) == 1:
            if typeList[conjuntions[0]].lower_ == "and":
                j = start
                while j < conjuntions[0]:
                    name = ""
                    while j not in commas and j < conjuntions[0]:
                        name += typeList[j].text + "_"
                        j += 1
                    # Keep heyphens without underscores in nouns
                    name = name.replace("_-_" ,"-")
                    glossaType.append(''.join([operators[2], str(typeStrings.index(name[:-1]))]))
                    glossaType.append(operators[0])
                    j += 1
                j = conjuntions[0] + 1
                name = ""
                while j < end and j not in commas:
                    name += typeList[j].text + "_"
                    j += 1
                # Keep heyphens without underscores in nouns
                name = name.replace("_-_" ,"-")
                glossaType.append(''.join([operators[2], str(typeStrings.index(name[:-1]))]))
            elif typeList[conjuntions[0]].lower_ == "or":
                j = start
                while j < conjuntions[0]:
                    name = ""
                    while j not in commas and j < conjuntions[0]:
                        name += typeList[j].text + "_"
                        j += 1
                    # Keep heyphens without underscores in nouns
                    name = name.replace("_-_" ,"-")
                    glossaType.append(''.join([operators[2], str(typeStrings.index(name[:-1]))]))
                    glossaType.append(operators[1])
                    j += 1
                j = conjuntions[0] + 1
                name = ""
                while j < end and j not in commas:
                    name += typeList[j].text + "_"
                    j += 1
                # Keep heyphens without underscores in nouns
                name = name.replace("_-_" ,"-")
                glossaType.append(''.join([operators[2], str(typeStrings.index(name[:-1]))]))
            return glossaType
        # If there is more than one conjuntion, recursivly break down the subtype
        else:
            mi = floor(len(conjuntions) / 2)
            middleIndex = conjuntions[mi]
            if typeList[middleIndex].lower_ == "and":
                l1 = self.GenerateKernelSectionGlossa(start, middleIndex, typeList, type) 
                l2 = self.GenerateKernelSectionGlossa(middleIndex + 1, end, typeList, type)
                return [l1, operators[0], l2]
            if typeList[middleIndex].lower_ == "or":
                l1 = self.GenerateKernelSectionGlossa(start, middleIndex, typeList, type) 
                l2 = self.GenerateKernelSectionGlossa(middleIndex + 1, end, typeList, type)
                return [l1, operators[1], l2]

    def GenerateKernelGlossa(self, start, end, glossa, kernelSeperators, kernelTimingBreak):
        kernels = [g.kernel for g in glossa]
        operators = ["#", "!", "#!"]
        glossaKernels = []
        # Find conjunctions and commas
        conjuntions = [sep for sep in kernelSeperators if (sep[0] == "and" or sep[0] == "or") and (sep[1] >= start and sep[1] < end)]
        commas = [sep for sep in kernelSeperators if sep[0] == "," and (sep[1] >= start and sep[1] < end)]
        currentKernels = [i for i in range(0, len(kernels)) if kernels[i].start >= start and kernels[i].end <= end]
        # If there is a timebreak, seperate the sentence
        if kernelTimingBreak is not None:
            l1 = self.GenerateKernelGlossa(start, kernelTimingBreak, glossa, kernelSeperators, None) 
            l2 = self.GenerateKernelGlossa(kernelTimingBreak + 1, end, glossa, kernelSeperators, None)
            return [l1, operators[2], l2]
        # If there is only one glossa in the sentence return it
        elif len(conjuntions) == 0:
            glossaKernels.append(glossa[currentKernels[0]])
            return glossaKernels
        # If there is one conjection in the sentence, get all of the glossa seperated by the appropreate operator
        elif len(conjuntions) == 1:
            if conjuntions[0][0] == "and":
                j = currentKernels[0]
                glossaKernels.append(glossa[j])
                j += 1
                while len(commas) > 0:
                    glossaKernels.append(operators[0])
                    glossaKernels.append(glossa[j])
                    j += 1
                    commas.pop()
                glossaKernels.append(operators[0])
                glossaKernels.append(glossa[j])
            elif conjuntions[0][0] == "or":
                j = currentKernels[0]
                glossaKernels.append(glossa[j])
                j += 1
                while len(commas) > 0:
                    glossaKernels.append(operators[1])
                    glossaKernels.append(glossa[j])
                    j += 1
                    commas.pop()
                glossaKernels.append(operators[1])
                glossaKernels.append(glossa[j])
            return glossaKernels
        else:
            # If there is more than one conjuntion, recursivly break down the sentence
            mi = floor(len(conjuntions) / 2)
            middleIndex = conjuntions[mi][1]
            if conjuntions[mi][0] == "and":
                l1 = self.GenerateKernelGlossa(start, middleIndex, glossa, kernelSeperators, kernelTimingBreak)
                l2 = self.GenerateKernelGlossa(middleIndex + 1, end, glossa, kernelSeperators, kernelTimingBreak)
                return [l1, operators[0], l2]
            if conjuntions[mi][0] == "or":
                l1 = self.GenerateKernelGlossa(start, middleIndex, glossa, kernelSeperators, kernelTimingBreak)
                l2 = self.GenerateKernelGlossa(middleIndex + 1, end, glossa, kernelSeperators, kernelTimingBreak)
                return [l1, operators[1], l2]
                    

                            

