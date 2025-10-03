class Kernel:
  def __init__(self, sentence, action, actionStrings, agent, agentStrings, patient, patientStrings):
      self.sentence = sentence
      self.agentStrings = agentStrings
      self.agent = agent
      self.actionStrings = actionStrings
      self.action = action
      self.patientStrings = patientStrings
      self.patient = patient
      self.timing = -1
      if len(self.agent) > 0:
        self.start = self.agent[0].i
      else:
        self.start = self.action[0].i
      if len(self.patient) > 0:
        self.end = self.patient[-1].i
      else:
        self.end = self.action[-1].i

  def __lt__(self,other): 
    return self.timing < other.timing