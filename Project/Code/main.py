from Kernel.KernelGenerator import KernelGenerator
from Glossa.GlossaGenerator import GlossaGenerator
from SPN.SPN import SPN
import spacy
nlp = spacy.load('en_core_web_lg')

# Get text input
numberOfRuns = input("How many times would you like to run the state machine? ")
text = input("Enter text: ")
# Seperate sentences
sentences = text.split(".")
while '' in sentences:
    sentences.remove('')
# Create objects that contain the kernels and glossa
kernelGenerator = KernelGenerator()
glossaGenerator = GlossaGenerator()
# Generate kernels for sentences
for sent in sentences:
    sent = sent.strip()
    kernelGenerator.AddKernelToKernelList(sent)
# Generate glossa for sentences
for index in range(0, len(kernelGenerator.kernelList)):
    glossaGenerator.AddSentenceToGlossa(kernelGenerator.kernelList[index], kernelGenerator.kenelSeperators[index], kernelGenerator.kernelTimingBreaks[index])
# Create and run state machine
for i in range(0, int(numberOfRuns)):
    print("Run " + str(i + 1) + ":")
    spn = SPN(glossaGenerator, 1, 100)
    spn.RunStateMachine(glossaGenerator.agentList, glossaGenerator.actionList, glossaGenerator.patientList)
    print()