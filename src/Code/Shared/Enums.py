import enum

class Phase(enum.Enum):
   PreAction = 1
   Action = 2
   PostAction = 3

class Type(enum.Enum):
    Agent = 1
    Action = 2
    Patient = 3

class TimingWord(enum.Enum):
   Before = 1
   After = 2