from Shared.Enums import Phase
## Represents a state in the state machine
class State:
    def __init__(self, id, transitionTime, action, actionState, agentState, patientState, affectedAgent, otherAgent, affectedPatient, otherPatient):
        # Unique ID number
        self.id = id
        # The time that this state was reached
        self.transitionTime = transitionTime
        # The action to be completed in the state
        self.action = action
        # The type of state (pre-action, action, post-action)
        self.actionState = actionState
        # Current state of the agents
        self.agentState = agentState
        # Current state of the patients
        self.patientState = patientState
        # Agents selected to perform the action
        self.affectedAgent = affectedAgent
        # Agents in the kernel not selected to comple the action (applicable when there is an or between agents)
        self.otherAgent = otherAgent
        # Patients selected to receive the action
        self.affectedPatient = affectedPatient
        # Patients in the kernel not selected to comple the action (applicable when there is an or between patients)
        self.otherPatient = otherPatient

    # Helper funtion to compare states and tokens with the same release time by ID
    def __lt__(self,other): 
        return self.id < other.id

    # Helper funtion to print contents of a state
    def PrintState(self, agentList, actionList, patientList, stateType):
        agentIndicies = [int(agent[1]) for agent in self.affectedAgent]
        printAgents = [agentList[agent] for agent in agentIndicies]
        actionIndicies = [int(action[1]) for action in self.action]
        printActions = [actionList[action] for action in actionIndicies]
        patientIndicies = [int(patient[1]) for patient in self.affectedPatient]
        printPatients = [patientList[patient] for patient in patientIndicies]
        if stateType == Phase.PreAction:
            phaseString = "Pre-Action"
        elif stateType == Phase.Action:
            phaseString = "Action"
        else:
            phaseString = "Post-Action"
        timeString = str(self.transitionTime)
        avpString = str(printAgents) + " -> " + str(printActions)  + " -> " + str(printPatients)
        print(f"{timeString : <10}{phaseString : ^20}{avpString : ^30}")