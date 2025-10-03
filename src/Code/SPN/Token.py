class Token:
    def __init__(self, id, releaseTime, transitionTimes, action, affectedAgent, otherAgent, affectedPatient, otherPatient):
        # Unique ID number
        self.id = id
        # The time that this token was reached
        self.releaseTime = releaseTime
        # The transition times for each state (pre-action, action, post-action)
        self.transitionTimes = transitionTimes
        # The action to be completed in the state
        self.action = action
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