
# Perform standard imports
import spacy
nlp = spacy.load('en_core_web_lg')
from Kernel.Kernel import Kernel
from Shared.Enums import TimingWord
import re
from math import floor
from random import randint

simultaniousWords = ["while", "simultaneous"]
simultaniousPhrases = ["at the same time", "in the meantime", "during that time"]
beforeWords = ["before", "earlier", "previous", "prior"]
afterWords = ["after", "later", "next"]

class KernelGenerator:
    def __init__(self):
        # List of all the kernels in a document
        self.kernelList = []
        # List of all the tokens that separate the kernels in a document
        self.kenelSeperators = []
        # List of all the timing breaks in a document (Produced by prepositional phrases)
        self.kernelTimingBreaks = []
        # List to keep track of sentence timing (order) in a document
        self.usedTimes = []

    def AddKernelToKernelList(self, doc):
        # Find all of the kernels in a sentence, and remove unecessay prepositional phrases from a sentence
        kernelList, kernelSeperators, docUpdated, containsStartorEndTimingBreak, timingWordMidIndex = self.GetKernels(nlp(doc))
        timingBreak = self.FindTimingBreak(kernelList, kernelSeperators, 0, len(docUpdated), containsStartorEndTimingBreak, timingWordMidIndex)
        # Determine/Update the timing of all of the kernels
        kernelList = self.DetermineOrder(docUpdated, kernelList, timingBreak)
        # Add individual sentence to  document kernel list
        self.kernelList.append(kernelList)
        self.kenelSeperators.append(kernelSeperators)
        self.kernelTimingBreaks.append(timingBreak)

    def FindNounSeperators(self, doc):
        # Find the last possible subject after a comma. 
        # If the seperation of patients and agents between two kernels is ambiguous, the greedy solution is chosen
        # The last possible noun is considered the subject
            canidates = []
            lastConj = None
            lastChunkIndex = -1
            chunks = list(doc.noun_chunks)
            for token in doc:
                if token.pos_ == "CCONJ":
                    lastConj = token.i
                elif token.dep_ == "nsubj" or token.dep_ == "nsubjpass":
                    return token.i
                elif (token.dep_ == "conj" and lastConj is not None):
                    k = 0
                    while token not in chunks[k]:
                        k += 1
                    chunk = chunks[k]
                    if (chunk[0].i - 1 != lastConj and k > 0 and (lastChunkIndex != k - 1)) or (k == len(chunks) - 1 and len(canidates) == 0):
                        canidates.append(token.i)
                        lastChunkIndex = k
            numCommas = 0
            canidateIndex = None
            firstIndex = doc[0].i
            for index in canidates:
                if doc[index - 2 - firstIndex].text == ",":
                    numCommas += 1
                    canidateIndex = index
            if numCommas < len(canidates) and numCommas > 0:
                return canidateIndex
            if len(canidates) > 0:
                return canidates[-1]
            return None

    def FindLastSubject(self, doc):
        # Find the last possible subject after a conjunction. 
        # If the seperation of patients and agents between two kernels is ambiguous, the greedy solution is chosen
        # The last possible noun is considered the subject
        canidates = []
        numCommas = 0
        for token in doc:
            if token.dep_ == "nsubj" or token.dep_ == "nsubjpass":
                return token.i
            elif token.pos_ == "PUNCT":
                numCommas += 1
            elif token.pos_ == "CCONJ":
                if numCommas < 2:
                    canidates.append(token.i + 1)
                numCommas = 0
        numCommas = 0
        canidateIndex = None
        firstIndex = doc[0].i
        for index in canidates:
            if doc[index - 2 - firstIndex].text == ",":
                numCommas += 1
                canidateIndex = index
        if numCommas < len(canidates)  and numCommas > 0:
            return canidateIndex
        if len(canidates) > 0:
            return canidates[-1]
        return None

    def RemoveBeginingPrepositions(self, doc):
        # Remove prepositional phrases that begin with before or after at the begining of a sentence      
        if doc[0].dep_ == "prep" and (doc[0].lower_ == "before" or doc[0].lower_ == "after"):
            index = self.FindNounSeperators(doc)
            if index is not None and doc[index - 2].tag_ != "DT":
                doc = nlp(doc[index:].text)
        return doc

    def FindClauses(self, doc):
        # Find the indicies of clause (kernel) agents and actions to determine where kernels are\
        #Remove prepositional phrases
        doc = self.RemoveBeginingPrepositions(doc)
        allVerbs = [i for i, token in enumerate(doc) if token.pos_ == "VERB" or token.pos_ == "AUX"]
        allConjuntions = [i for i, token in enumerate(doc) if (token.text == "," or token.text == "and" or token.text == "or")]
        clause_starts = []
        clause_ends = []
        lastVerbIndex = None
        # Find main verbs
        for i, index in enumerate(allVerbs):
            if i == 0:
                j = 1
                while doc[index + j].pos_ == "ADP" or doc[index + j].pos_ == "PART":
                    j += 1
                j -= 1
                clause_ends.append(index + j)
                lastVerbIndex = index + j
            else:
                if lastVerbIndex + 1 != index and lastVerbIndex + 2 != index and lastVerbIndex + 3 != index:
                    j = 1
                    while doc[index + j].pos_ == "ADP" or doc[index + j].pos_ == "PART":
                        j += 1
                    j -= 1
                    # Update clause ends if verbs aren't seperatwd by nouns
                    ignorePOS = ["NOUN", "PRON", "PROPN", "ADJ", "DET"]
                    ignoreDEP = ["agent"]
                    ignoreTAG = ["POS", "."]
                    if all(doc[i].pos_ not in ignorePOS and 
                    doc[i].dep_ not in ignoreDEP and
                    doc[i].tag_ not in ignoreTAG and
                    (doc[i].dep_ != "prep" or doc[i].pos_ == "ADP") and
                    (doc[i].tag_ != "IN" or doc[i].pos_ == "ADP") for i in range(lastVerbIndex + 1, index)):
                        clause_ends[-1] = index + j
                    else:
                        clause_ends.append(index + j)
                lastVerbIndex = index + j
        index = 1
        # Get first subject and find timing break because that will determine the subjects
        clause_starts.append(0)
        containsStartorEndTimingBreak = (any(word in doc[0].lower_ for word in simultaniousWords) or
        (any(word in doc[0].lower_ for word in beforeWords) or any(word in doc[len(doc) - 1].lower_ for word in beforeWords)) or 
        (any(word in doc[0].lower_ for word in afterWords) or any(word in doc[len(doc) - 1].lower_ for word in afterWords)))
        timingWordMidIndex = None
        # Find subjects based on the number of verbs
        while index < len(clause_ends):
            docSection = doc[clause_ends[index - 1]:clause_ends[index]]
            i = 0
            while docSection[i].i in allVerbs or docSection[i].i in allConjuntions:
                i += 1
            docSection = docSection[i:]
            # check for simultanious words
            timingWordIndexes = [i for i in range(0, len(docSection)) if (any(word in docSection[i].lower_ for word in simultaniousWords) or
            any(word in docSection[i].lower_ for word in beforeWords) or any(word in docSection[i].lower_ for word in afterWords))]
            if len(timingWordIndexes) > 0:
                clause_starts.append((timingWordIndexes[0] + clause_ends[index - 1] + i + 1))
                timingWordMidIndex = timingWordIndexes[0] + clause_ends[index - 1] + i
            elif len(clause_ends) > 2:
                if index < len(clause_ends) - 1:
                    clause_starts.append(self.FindNounSeperators(docSection))
                else:
                    clause_starts.append(self.FindLastSubject(docSection))
            else:
                    if containsStartorEndTimingBreak:
                        clause_starts.append(self.FindNounSeperators(docSection))
                    else:
                        clause_starts.append(self.FindLastSubject(docSection))
            index += 1
                    
        # Remove prepositional phrases that don't contain a kernel, and update agent and action indicies accordingly
        ignorePOS = ["NOUN", "PRON", "PROPN", "ADJ","ADV"]
        prepositionsAfterLastVerb = [i for i in range(clause_ends[-1] + 1, len(doc)) if doc[i].lower_ == "before" or doc[i].lower_ == "after"]
        if len(prepositionsAfterLastVerb) > 0:
            nounsAfterLastPreposition = [i for i in range(prepositionsAfterLastVerb[-1] + 1, len(doc)) if doc[i].pos_ in ignorePOS and doc[i].tag_ != "DT"]
        else:
            nounsAfterLastPreposition = [] 
        if len(nounsAfterLastPreposition) > 0:
            doc = nlp(doc[:prepositionsAfterLastVerb[-1] - 1].text)
        return clause_starts, clause_ends, doc, containsStartorEndTimingBreak, timingWordMidIndex

    def FindSeperators(self, doc, clause_starts, clause_ends):
        # Find all of the commas and conjunctions in a sentence
        seperators = []
        if len(clause_starts) == 1:
            return seperators
        else:
            j = 1
            while j < len(clause_ends):
                tempList = [(doc[i].text, i) for i in range(clause_ends[j - 1], clause_starts[j] + 1) 
                if doc[i].pos_ == "CCONJ" or doc[i].pos_ == "PUNCT"]
                if len(tempList) > 0:
                    seperators.append(tempList[len(tempList) - 1])
                j += 1
            return seperators  

    def FindVP(self, doc, start, end):
        # Find the verbs in the kernel indicies
        # Ignore non verb tokens
        ignorePOS = ["NOUN", "PRON", "PROPN", "ADJ", "DET"]
        ignoreDEP = ["agent"]
        ignoreTAG = ["POS", "."]
        verbs = [token for i, token in enumerate(doc)  if i >= start and i < end and
        token.pos_ not in ignorePOS and 
        token.dep_ not in ignoreDEP and
        token.tag_ not in ignoreTAG and
        (token.dep_ != "prep" or token.pos_ == "ADP") and
        (token.tag_ != "IN" or token.pos_ == "ADP")]
        # Remove trailing and leading conjunctions and punctuation
        while verbs[-1].pos_ == "CCONJ" or verbs[-1].pos_ == "PUNCT":
            verbs = verbs[:-1]
        while verbs[0].pos_ == "CCONJ" or verbs[0].pos_ == "PUNCT":
            verbs = verbs[1:]
        # Only keep consecutive verbs
        lastConsecVerb = None
        foundLastConsecVerb = False
        for i, verb in enumerate(verbs):
            if i > 0 and not foundLastConsecVerb:
                if verb.i - verbs[i - 1].i != 1:
                    lastConsecVerb = i
                    foundLastConsecVerb = True
        if lastConsecVerb is not None:
            verbs = verbs[:lastConsecVerb]
        # Remove trailing and leading conjunctions and punctuation
        while verbs[-1].pos_ == "CCONJ" or verbs[-1].pos_ == "PUNCT":
            verbs = verbs[:-1]
        while verbs[0].pos_ == "CCONJ" or verbs[0].pos_ == "PUNCT":
            verbs = verbs[1:]
        # Determine the position of adverbs around main verbs and if there are multiple adverbs
        multipleAdverbs = False
        adverbsAfterVerb = False
        mainVerbs = [i for i in range(0, len(verbs)) if verbs[i].pos_ == "VERB"]
        for i, verbIndex in enumerate(mainVerbs):
            if not multipleAdverbs:
                if i == 0:
                    adverbsBefore = [i for i in range(0, verbIndex) if verbs[i].pos_ == "ADV"]
                    if len(mainVerbs) == 1:
                        adverbsAfter = [i for i in range(verbIndex + 1, len(verbs)) if verbs[i].pos_ == "ADV"]
                    else:
                        adverbsAfter = [i for i in range(verbIndex + 1, mainVerbs[i + 1]) if verbs[i].pos_ == "ADV"]
                        if len(adverbsAfter) > 0 and adverbsAfter[-1] + 1 == mainVerbs[i + 1]:
                            adverbsAfter.pop(-1)
                    if len(adverbsBefore) > 1:
                        multipleAdverbs = True
                    elif len(adverbsAfter) > 1:
                        if all(verbs[index].pos_ != "CCONJ" and verbs[index].text != "," for index in range(verbIndex + 1, adverbsAfter[0])):
                            multipleAdverbs = True
                            adverbsAfterVerb = True
                elif i == len(mainVerbs) - 1:
                    adverbsBefore = [i for i in range(mainVerbs[i - 1] + 1, verbIndex) if verbs[i].pos_ == "ADV"]
                    if len(adverbsBefore) > 0 and (adverbsBefore[0] - 1 == mainVerbs[i - 1]):
                            adverbsBefore.pop(-1)
                    adverbsAfter = [i for i in range(verbIndex + 1, len(verbs)) if verbs[i].pos_ == "ADV"]
                    if len(adverbsAfter) > 1:
                        multipleAdverbs = True
                        adverbsAfterVerb = True
                    elif len(adverbsBefore) > 1:
                        if all(verbs[index].pos_ != "CCONJ" and verbs[index].text != "," for index in range(adverbsBefore[-1], verbIndex)):
                            multipleAdverbs = True
                else:
                    adverbsBefore = [i for i in range(mainVerbs[i - 1] + 1, verbIndex) if verbs[i].pos_ == "ADV"]
                    adverbsAfter = [i for i in range(verbIndex + 1, mainVerbs[i + 1]) if verbs[i].pos_ == "ADV"]
                    if len(adverbsBefore) > 0 and (adverbsBefore[0] - 1 == mainVerbs[i - 1]):
                            adverbsBefore.pop(-1)
                    if len(adverbsAfter) > 0 and adverbsAfter[-1] + 1 == mainVerbs[i + 1]:
                            adverbsAfter.pop(-1)
                    if len(adverbsBefore) > 1:
                        if all(verbs[index].pos_ != "CCONJ" and verbs[index].text != "," for index in range(adverbsBefore[-1], verbIndex)):
                            multipleAdverbs = True
                    elif len(adverbsAfter) > 1:
                        if all(verbs[index].pos_ != "CCONJ" and verbs[index].text != "," for index in range(verbIndex + 1, adverbsAfter[0])):
                            multipleAdverbs = True
                            adverbsAfterVerb = True
        if multipleAdverbs:
            if adverbsAfterVerb:
                verbs.reverse()
            # Remove commas and conjuntions between advebs before the verb
            newVerbs = []
            firstAdverb = None
            for i, token in enumerate(verbs):
                if token.pos_ == "VERB":
                    if firstAdverb is not None:
                        subList = [verbs[j] for j in range(firstAdverb, i + 1) if verbs[j].text != "," and verbs[j].pos_ != "CCONJ"]
                        newVerbs.extend(subList)
                        firstAdverb = None
                    else:
                        newVerbs.append(token)
                elif token.pos_ == "ADV" and firstAdverb is None:
                    firstAdverb = i
                elif (token.text == "," or token.pos_ == "CCONJ") and firstAdverb is None:
                        newVerbs.append(token)
            if adverbsAfterVerb:
                newVerbs.reverse()
            verbs = newVerbs
        # Check for "by" to flip agents and patients
        flipAP = False
        if len(verbs) > 1:
            byVerbs = [verbs[i].i for i in range(1, len(verbs)) if verbs[i].tag_ == "VBN" and verbs[i - 1].tag_ == "VBD"]
            for index in byVerbs:
                j = 1
                while doc[index + j].pos_ == "ADV":
                    j += 1
                if doc[index + j].lower_ == "by":
                    flipAP = True
        # Determine verb strings (for glossa to kernel conversions)
        strs = [token.text for token in verbs]
        str = "_".join(strs)
        verbStrings = re.split('_,_and_|_,_or_|_,_|_and_|_or_', str)
        verbIndices = [token.i for token in doc if token in verbs]
        return verbs, verbIndices, verbStrings, flipAP

    def FindNP(self, doc, start, end, vp):
        # Find the noun in the kernel indicies
        # Ignore non noun tokens
        ignorePOS = ["DET", "ADP", "ADJ", "ADV", "PART"]
        ignoreNOUNS = ["pm", "tonight", "week", "year", "years", "month", "months", "yesterday", "meantime", "same"]
        ignoreTAG = ["IN", ".", "POS", "DT"]
        activeVerb = False
        # Determine if verb is in active voice
        for verb in vp:
            if verb.tag_ == "VBD" and verb.dep_ == "ROOT":
                activeVerb = True
        nouns = [token for i, token in enumerate(doc) if i >= start and i < end and 
        token.pos_ not in ignorePOS and 
        token.lower_ not in ignoreNOUNS and 
        (token.dep_ != "compound" or nlp(token.lower_)[0].pos_ != "ADJ" or (doc[i + 1].text == "-" and i < len(doc) - 1)) and
        (token.tag_ not in ignoreTAG) and 
        (token.lower_ != "time" or token.dep_ != "pobj") 
        and (token.tag_ != "PRP" or (activeVerb == False or token.dep_  != "pobj"))]
        # If there are no nouns, check for adjectives
        if len(nouns) == 0:
            ignorePOS.remove("ADJ")
            nouns = [token for i, token in enumerate(doc) if i >= start and i < end and 
            token.pos_ not in ignorePOS and 
            token.lower_ not in ignoreNOUNS and 
            (token.dep_ != "compound" or nlp(token.lower_).pos_ != "ADJ" or (doc[i + 1].text == "-" and i < len(doc) - 1)) and
            (token.tag_ not in ignoreTAG) and 
            (token.lower_ != "time" or token.dep_ != "pobj") 
        and (token.tag_ != "PRP" or (activeVerb == False or token.dep_  != "pobj"))]
        if len(nouns) > 0:
            # Remove trailing and leading conjunctions and punctuation
            while nouns[-1].pos_ == "CCONJ" or nouns[-1].pos_ == "PUNCT":
                nouns = nouns[:-1]
            while nouns[0].pos_ == "CCONJ" or nouns[0].pos_ == "PUNCT":
                nouns = nouns[1:]
            # Remove all conjunctions except the first one after a noun (This is for if multiple adjetives are describing a noun)
            nouns = [noun for i, noun in enumerate(nouns) if ((noun.pos_ != "CCONJ" and noun.pos_ != "PUNCT") or 
            (nouns[i - 1].pos_ != "CCONJ" and nouns[i - 1].pos_ != "PUNCT") or
            (i >= 2 and (nouns[i - 2].pos_ != "CCONJ" and nouns[i - 2].pos_ != "PUNCT") and nouns[i - 1].pos_ == "PUNCT"))]
            # Determine noun strings (for glossa to kernel conversions)
            strs = [token.text for token in nouns]
            str = "_".join(strs)
            # Keep heyphens without underscores in nouns
            str = str.replace("_-_" ,"-")
            nounStrings = re.split('_,_and_|_,_or_|_,_|_and_|_or_', str)
        else:
            nounStrings = []
        return nouns, nounStrings

    def GetKernels(self, doc):
        currentKernelList = []
        # Find where clauses start and end
        clause_starts, clause_ends, doc, containsStartorEndTimingBreak, timingWordMidIndex = self.FindClauses(doc)
        clause_seperators = self.FindSeperators(doc, clause_starts, clause_ends)
        # If there is one kernel
        if len(clause_seperators) == 0:
            vp, vpIndices, vpStrings, flipAp = self.FindVP(doc, clause_starts[0] + 1, len(doc))
            agent, agentStrings = self.FindNP(doc, 0, vpIndices[0], vp)
            patient, patientStrings = self.FindNP(doc, vpIndices[-1] + 1, len(doc), vp)
            if flipAp:
                currentKernelList.append(Kernel(doc, vp, vpStrings, patient, patientStrings, agent, agentStrings))
            else:
                currentKernelList.append(Kernel(doc, vp, vpStrings, agent, agentStrings, patient, patientStrings))
        # If there are two kernels
        elif len(clause_seperators) == 1:
                vp1, vp1Indices, vp1Strings, flipAp = self.FindVP(doc, clause_starts[0] + 1, clause_seperators[0][1])
                agent1, agent1Strings = self.FindNP(doc, 0, vp1Indices[0], vp1)
                patient1, patient1Strings = self.FindNP(doc, vp1Indices[-1] + 1, clause_seperators[0][1], vp1)
                if flipAp:
                    currentKernelList.append(Kernel(doc, vp1, vp1Strings, patient1, patient1Strings, agent1, agent1Strings))
                else:
                    currentKernelList.append(Kernel(doc, vp1, vp1Strings, agent1, agent1Strings, patient1, patient1Strings))
                vp2, vp2Indices, vp2Strings, flipAp = self.FindVP(doc, clause_seperators[0][1] + 1, len(doc))
                agent2, agent2Strings = self.FindNP(doc, clause_seperators[0][1] + 1, vp2Indices[0], vp2)
                patient2, patient2Strings = self.FindNP(doc, vp2Indices[-1] + 1, len(doc), vp2)
                if flipAp:
                    currentKernelList.append(Kernel(doc, vp2, vp2Strings, patient2, patient2Strings, agent2, agent2Strings))
                else:
                    currentKernelList.append(Kernel(doc, vp2, vp2Strings, agent2, agent2Strings, patient2, patient2Strings))
        # If there are three or more kernels
        elif len(clause_seperators) > 1:
            i = 0
            while i < len(clause_seperators):
                # Getting the first kernel
                if i == 0:
                    vp, vpIndices, vpStrings, flipAp = self.FindVP(doc, clause_starts[0] + 1, clause_seperators[i][1])
                    agent, agentStrings = self.FindNP(doc, 0, vpIndices[0], vp)
                    patient, patientStrings = self.FindNP(doc, vpIndices[-1] + 1, clause_seperators[i][1], vp)
                    if flipAp:
                        currentKernelList.append(Kernel(doc, vp, vpStrings, patient, patientStrings, agent, agentStrings))
                    else:
                        currentKernelList.append(Kernel(doc, vp, vpStrings, agent, agentStrings, patient, patientStrings))
                # Getting the last twwo kernels
                elif i == len(clause_seperators) - 1:
                    vp1, vp1Indices, vp1Strings, flipAp = self.FindVP(doc, clause_seperators[i - 1][1] + 1, clause_seperators[i][1] - 1)
                    agent1, agent1Strings = self.FindNP(doc, clause_seperators[i - 1][1] + 1, vp1Indices[0], vp1)
                    patient1, patient1Strings = self.FindNP(doc, vp1Indices[-1] + 1, clause_seperators[i][1], vp1)
                    if flipAp:
                        currentKernelList.append(Kernel(doc, vp1, vp1Strings,  patient1, patient1Strings, agent1, agent1Strings))
                    else:
                        currentKernelList.append(Kernel(doc, vp1, vp1Strings, agent1, agent1Strings, patient1, patient1Strings))
                    vp2, vp2Indices, vp2Strings, flipAp = self.FindVP(doc, clause_seperators[i][1] + 1, len(doc))
                    agent2, agent2Strings = self.FindNP(doc, clause_seperators[i][1] + 1, vp2Indices[0], vp2)
                    patient2, patient2Strings = self.FindNP(doc, vp2Indices[-1] + 1, len(doc), vp2)
                    if flipAp:
                        currentKernelList.append(Kernel(doc, vp2, vp2Strings, patient2, patient2Strings, agent2, agent2Strings))
                    else:
                        currentKernelList.append(Kernel(doc, vp2, vp2Strings, agent2, agent2Strings, patient2, patient2Strings))
                # Getting the intermediate kernels
                else:
                    vp, vpIndices, vpStrings, flipAp = self.FindVP(doc, clause_seperators[i - 1][1] + 1, clause_seperators[i][1])
                    agent, agentStrings = self.FindNP(doc, clause_seperators[i - 1][1] + 1, vpIndices[0], vp)
                    patient, patientStrings = self.FindNP(doc, vpIndices[-1] + 1, clause_seperators[i][1], vp)
                    if flipAp:
                        currentKernelList.append(Kernel(doc, vp, vpStrings, patient, patientStrings, agent, agentStrings))
                    else:
                        currentKernelList.append(Kernel(doc, vp, vpStrings, agent, agentStrings, patient, patientStrings))
                i += 1
        return currentKernelList, clause_seperators, doc, containsStartorEndTimingBreak, timingWordMidIndex

    def FindTimingBreak(self, kernels, kernelSeperators, start, end, containsStartorEndTimingBreak, timingWordMidIndex):
        # Determine where there is a timing break between two kernels because of a prepositional phrase
        # If the timing word is at the begining or end of a sentence, use recursion to find the timing break
        if containsStartorEndTimingBreak:
            conjuntions = [sep for sep in kernelSeperators if (sep[0] == "and" or sep[0] == "or") and (sep[1] >= start and sep[1] < end)]
            commas = [sep for sep in kernelSeperators if sep[0] == "," and (sep[1] >= start and sep[1] < end)]
            currentKernels = [i for i in range(0, len(kernels)) if kernels[i].start >= start and kernels[i].end <= end]
            if len(conjuntions) > 0:
                lastConjuntionIndex = conjuntions[-1][1]
                kernelIndex = 0
                while kernels[currentKernels[kernelIndex]].start < lastConjuntionIndex:
                    kernelIndex += 1
                if kernelIndex + 1 < len(currentKernels):
                    pauseIndex = kernels[currentKernels[kernelIndex]].end + 1
                    return pauseIndex
                else:
                    mi = floor(len(conjuntions) / 2)
                    middleIndex = conjuntions[mi][1]
                    return self.FindTimingBreak(kernels, kernelSeperators, start, middleIndex, containsStartorEndTimingBreak, timingWordMidIndex)
            elif len(commas) == 1:
                return commas[0][1]
            else:
                return None
        # There is a timing word mid sentence
        elif timingWordMidIndex is not None:
            return timingWordMidIndex - 1
        else:
            # There's no timing words in the sentence
            return None
            

    def DetermineOrder(self, doc, currentKernelList, timingBreak):
        updatedTiming = False
        # check for simultanious phases
        simultaniousPhraseIndexes = [doc.text.lower().find(simultaniousPhrase) for simultaniousPhrase in simultaniousPhrases]
        # check for simultainous words
        simultaniousWordIndexes = [i for i in range(0, len(doc)) if any(word in doc[i].lower_ for word in simultaniousWords)]
        # check for before words
        beforeWordIndexes = [(i, TimingWord.Before) for i in range(0, len(doc)) 
        if (any(word in doc[i].lower_ for word in beforeWords) and doc[i - 1].lower_ == "and")
        or (any(word in doc[i].lower_ for word in beforeWords) and (i == 0 or i == len(doc) - 1))]
        # check for after words
        afterWordIndexes = [(i, TimingWord.After) for i in range(0, len(doc)) 
        if (any(word in doc[i].lower_ for word in afterWords) and doc[i - 1].lower_ == "and")
        or (any(word in doc[i].lower_ for word in afterWords) and (i == 0 or i == len(doc) - 1))]
        # Combine the lists, sorted by index
        combinedWords = []
        combinedWords.extend(beforeWordIndexes)
        combinedWords.extend(afterWordIndexes)
        combinedWords.sort()

        if any(simultaniousPhraseIndex > -1 for simultaniousPhraseIndex in simultaniousPhraseIndexes) or len(simultaniousWordIndexes) > 0:
            updatedTiming = True
            if timingBreak is None:
                # same timing for this sentence and previous sentence 
                timing = self.kernelList[-1][0].timing
                for kernel in currentKernelList:
                    kernel.timing = timing
            else:
                # same timing for this sentence
                timing = randint(0, 1000)
                while timing in self.usedTimes:
                    timing = randint(0, 1000)
                self.usedTimes.append(timing)
                for kernel in currentKernelList:
                    kernel.timing = timing
        # Do timing for before and after wods
        if len(combinedWords) > 0:
            updatedTiming = True
            while len(combinedWords) > 0:
                w = combinedWords.pop(0)
                index = w[0]
                type = w[1]
                if type == TimingWord.Before:
                    currentKernelList = self.GetNextBeforeWord(index, doc, timingBreak, currentKernelList)
                else:
                    currentKernelList = self.GetNextAfterWord(index, doc, timingBreak, currentKernelList)
                self.usedTimes = list(set(self.usedTimes))
        # If the kernel and surrounding kernels are not associated with timing words assign random time
        if not updatedTiming:
            timing = randint(0, 1000)
            while timing in self.usedTimes:
                timing = randint(0, 1000)
            self.usedTimes.append(timing)
            for kernel in currentKernelList:
                kernel.timing = timing
        return currentKernelList

    def GetNextAfterWord(self, index, doc, timingBreak, currentKernelList):
        firstTimeSet = False
        if index > 0 and index < len(doc) - 1:
            # time later after and or after timebreak
            kernelNumber = 0
            while currentKernelList[kernelNumber].end < index:
                kernelNumber += 1
            timing = max([currentKernelList[i].timing for i in range(0, kernelNumber)])
            if timing == -1:
                firstTimeSet = True
                timing = randint(0, 1000)
                while timing in self.usedTimes:
                    timing = randint(0, 1000)
            self.usedTimes.extend([i for i in range(timing, timing + 3)])
            for kernel in currentKernelList:
                if kernel.start >= index:
                    kernel.timing = timing + 1
                elif firstTimeSet:
                    kernel.timing = timing
        else:
            if timingBreak is None:
                # previous sentence is earlier
                timing = max([kernel.timing for kernel in self.kernelList[-1]])
                for kernel in currentKernelList:
                    kernel.timing = timing + 1
                self.usedTimes.extend([i for i in range(timing, timing + 3)])
            else:
                timing = randint(0, 1000)
                while timing in self.usedTimes:
                    timing = randint(0, 1000)
                self.usedTimes.extend([i for i in range(timing, timing + 3)])
                if len(doc) - index > index - 0:
                    # before time break is earlier
                    for kernel in currentKernelList:
                        if kernel.start >= index and kernel.end < timingBreak:
                            kernel.timing = timing
                        else:
                            kernel.timing = timing + 1
                else:
                    # after time break is earlier
                    for kernel in currentKernelList:
                        if kernel.start >= index and kernel.end < timingBreak:
                            kernel.timing = timing + 1
                        else:
                            kernel.timing = timing
        return currentKernelList

    def GetNextBeforeWord(self, index, doc, timingBreak, currentKernelList):
        firstTimeSet = False
        if index > 0 and index < len(doc) - 1:
            # time earlier after and or after timebreak
            kernelNumber = 0
            while currentKernelList[kernelNumber].end < index:
                kernelNumber += 1
            timing = min([currentKernelList[i].timing for i in range(0, kernelNumber)])
            if timing == -1:
                firstTimeSet = True
                timing = randint(0, 1000)
                while timing in self.usedTimes:
                    timing = randint(0, 1000)
            self.usedTimes.extend([i for i in range(timing - 2, timing + 1)])
            for kernel in currentKernelList:
                if kernel.start >= index:
                    kernel.timing = timing - 1
                elif firstTimeSet:
                    kernel.timing = timing
        else:
            if timingBreak is None:
                # previous sentence is later
                timing = min([kernel.timing for kernel in self.kernelList[-1]])
                for kernel in currentKernelList:
                    kernel.timing = timing - 1
                self.usedTimes.extend([i for i in range(timing - 2, timing + 1)])
            else:
                timing = randint(0, 1000)
                while timing in self.usedTimes:
                    timing = randint(0, 1000)
                self.usedTimes.extend([i for i in range(timing, timing + 3)])
                if len(doc) - index > index - 0:
                    # after time break is earlier
                    for kernel in currentKernelList:
                        if kernel.start >= index and kernel.end < timingBreak:
                            kernel.timing = timing + 1
                        else:
                            kernel.timing = timing
                else:
                    # before time break is earlier
                    for kernel in currentKernelList:
                        if kernel.start >= index and kernel.end < timingBreak:
                            kernel.timing = timing
                        else:
                            kernel.timing = timing + 1
        return currentKernelList