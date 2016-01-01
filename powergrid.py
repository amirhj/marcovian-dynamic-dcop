import numpy.random as ran
import random, sys
from util import Counter

class Node:
    def __init__(self, id, loads, generators, powergrid, rlParams, iResources, parent=None, debugLevel=1):
        self.id = id
        self.powerGrid = powergrid
        self.loads = { l:self.powerGrid.loads[l] for l in loads }
        self.generators = { g:self.powerGrid.generators[g] for g in generators }
        self.iResources = { i:self.powerGrid.iResources[i] for i in iResources }
        self.parent = parent
        self.messageBox = []
        self.OPCStates = {}
        # state are 1: Waiting for doing phase1, 2: Waiting for doing phase2
        self.state = 1
        self.isFinished = False
        self.stateLog = []
        self.PCStates = {}
        self.debugLevel = debugLevel

        # RL parameters
        self.rl = rlParams
        self.qvalues = Counter()
        self.actions = set()
        self.states = set()
        self.finalResult = None
        self.prevFinalResult = None
        self.learningResult = None
        self.prevLearningResult = None
        self.learningMessageBox = []
        self.learningStateLog = []

    def isRoot(self):
        if self.parent == None:
            return True
        return False

    def isLeaf(self):
        return self.powerGrid.isLeaf(self.id)

    def getChildren(self):
        return self.powerGrid.getChildren(self.id)

    def getParent(self):
        return self.powerGrid.grid[self.parent]

    def readMessageBox(self):
        messages = { m.sender: m for m in self.messageBox }
        self.stateLog.append({'recived Inbox': [{'from':m, 'content':str(messages[m].content) } for m in messages ] })
        del self.messageBox[:]
        return messages

    def readLearningMessageBox(self):
        messages = { m.sender: m for m in self.learningMessageBox }
        self.stateLog.append({'recived Learning Inbox': [{'from':m, 'content':str(messages[m].content) } for m in messages ] })
        del self.learningMessageBox[:]
        return messages

    def calculateValues(self):
        self.values = []

        if self.isLeaf():
            self.stateLog.append({})
            # Cartesian Product Matrix columns indecies of Generators and Intermittent resources and their size
            CPMGI = { g:{ 'index':0, 'size':len(self.generators[g].domain()) } for g in self.generators }

            if len(CPMGI) > 0:
                # making cartesian product of generators values
                firstG = self.generators.keys()[0]
                while CPMGI[firstG]['index'] < CPMGI[firstG]['size']:
                    sum_generators_outputs = sum([ self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators ])
                    sum_loads = sum(self.loads.values())
                    rFlow = sum_generators_outputs + sum_loads

                    sum_costs_generators = sum([ self.generators[g].domain()[ CPMGI[g]['index'] ] * self.generators[g].CI for g in self.generators ])
                    if abs(rFlow) <= self.capacityOfLineToParent():
                        flowCO = (rFlow, sum_costs_generators)
                        self.OPCStates[flowCO] = { g: self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators }
                        self.values.append(flowCO)

                    for i in reversed(self.generators.keys()):
                        if CPMGI[i]['index'] < CPMGI[i]['size']:
                            CPMGI[i]['index'] += 1
                            if CPMGI[i]['index'] == CPMGI[i]['size']:
                                if i != firstG:
                                    CPMGI[i]['index'] = 0
                            else:
                                break
        else:
            # Minimum power cost state of childern for each flowCO
            self.PCStates = {}

            MinStates = {}

            messages = self.readMessageBox()

            if len(self.generators) > 0:
                # Cartesian Product Matrix columns indecies of Generators and Intermittent resources and their size
                CPMGI = { g:{ 'index':0, 'size':len(self.generators[g].domain()) } for g in self.generators }

                # making cartesian product of generators values
                firstG = self.generators.keys()[0]
                while CPMGI[firstG]['index'] < CPMGI[firstG]['size']:
                    minPowerCost = 0
                    minPCState = None
                    rFlow = 0

                    # Cartesian Product Matrix columns Indecies of Messages and their size
                    CPMMI = { m:{ 'index':0, 'size':len(messages[m].content) } for m in messages }

                    # making cartesian product of children's messages and choosing the one with minimum cost
                    firstM = messages.keys()[0]
                    while CPMMI[firstM]['index'] < CPMMI[firstM]['size']:
                        sum_costs_generators = sum([ self.generators[g].domain()[ CPMGI[g]['index'] ] * self.generators[g].CI for g in self.generators ])
                        sum_costs_children = sum([ messages[m].content[ CPMMI[m]['index'] ][1] for m in messages ])
                        rCO = sum_costs_generators + sum_costs_children

                        sum_generators_outputs = sum([ self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators ])
                        sum_flows_children = sum([ messages[m].content[ CPMMI[m]['index'] ][0] for m in messages ])
                        sum_loads = sum(self.loads.values())
                        rFlow = sum_generators_outputs + sum_loads + sum_flows_children

                        if abs(rFlow) <= self.capacityOfLineToParent():
                            minPCState = tuple([ (m, messages[m].content[ CPMMI[m]['index'] ]) for m in messages ])
                            gens = { g: self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators }
                            # choosing minimum cost
                            if rFlow in MinStates:
                                if MinStates[rFlow][0] < rCO:
                                    MinStates[rFlow] = [rCO, minPCState, gens]
                            else:
                                MinStates[rFlow] = [rCO, minPCState, gens]

                        for i in reversed(messages.keys()):
                            if CPMMI[i]['index'] < CPMMI[firstM]['size']:
                                CPMMI[i]['index'] += 1
                                if CPMMI[i]['index'] == CPMMI[i]['size']:
                                    if i != firstM:
                                        CPMMI[i]['index'] = 0
                                else:
                                    break

                    for i in reversed(self.generators.keys()):
                        if CPMGI[i]['index'] < CPMGI[i]['size']:
                            CPMGI[i]['index'] += 1
                            if CPMGI[i]['index'] == CPMGI[i]['size']:
                                if i != firstG:
                                    CPMGI[i]['index'] = 0
                            else:
                                break
            else:
                # Cartesian Product Matrix columns Indecies of Messages and their size
                CPMMI = { m:{ 'index':0, 'size':len(messages[m].content) } for m in messages }

                # making cartesian product of children's messages and choosing the one with minimum cost
                firstM = messages.keys()[0]
                while CPMMI[firstM]['index'] < CPMMI[firstM]['size']:
                    sum_costs_children = sum([ messages[m].content[ CPMMI[m]['index'] ][1] for m in messages ])
                    rCO = sum_costs_children

                    sum_flows_children = sum([ messages[m].content[ CPMMI[m]['index'] ][0] for m in messages ])
                    sum_loads = sum(self.loads.values())
                    rFlow = sum_loads + sum_flows_children

                    if abs(rFlow) <= self.capacityOfLineToParent():
                        minPCState = tuple([ (m, messages[m].content[ CPMMI[m]['index'] ]) for m in messages ])
                        gens = { g: self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators }
                        # choosing minimum cost
                        if rFlow in MinStates:
                            if MinStates[rFlow][0] < rCO:
                                MinStates[rFlow] = [rCO, minPCState, gens]
                        else:
                            MinStates[rFlow] = [rCO, minPCState, gens]

                    for i in reversed(messages.keys()):
                        if CPMMI[i]['index'] < CPMMI[firstM]['size']:
                            CPMMI[i]['index'] += 1
                            if CPMMI[i]['index'] == CPMMI[i]['size']:
                                if i != firstM:
                                    CPMMI[i]['index'] = 0
                            else:
                                break

            #sss
            for rFlow in MinStates:
                flowCO = (rFlow, MinStates[rFlow][0])
                self.PCStates[flowCO] = MinStates[rFlow][1]
                self.OPCStates[flowCO] = MinStates[rFlow][2]
                self.values.append(flowCO)

        self.sendMessageToParent()

    def sendMessageToParent(self):
        if not self.isRoot():
            m = Message(self.id, self.parent, self.values)
            self.stateLog[-1]['sent'] = [{ 'to':self.parent, 'content':str(self.values) }]
            if self.debugLevel >= 2:
                print "Node ",self.id," to parent ",self.parent,self.values," ",len(self.values)
            self.powerGrid.grid[self.parent].messageBox.append(m)

    def sendLearningMessageToParent(self, value):
        if not self.isRoot():
            m = Message(self.id, self.parent, value)
            self.learningStateLog[-1]['sent'] = [{ 'to':self.parent, 'content':value }]
            if self.debugLevel >= 2:
                print "Node ",self.id," to parent ",self.parent,value," Learning Inbox"
            self.powerGrid.grid[self.parent].learningMessageBox.append(m)

    def propagateValues(self):
        messages = self.readMessageBox()
        if self.isRoot():
            isFirst = True
            minPowerCost = 0
            minPCState = None
            minGenerator = 0
            rFlow = 0
            minFlow = 0

            if len(self.generators) > 0:
                # Cartesian Product Matrix columns Indecies of Generators and Intermittent resources and their size
                CPMGI = { g:{ 'index':0, 'size':len(self.generators[g].domain()) } for g in self.generators }

                # making cartesian product of generators values
                firstG = self.generators.keys()[0]
                while CPMGI[firstG]['index'] < CPMGI[firstG]['size']:
                    # Cartesian Product Matrix columns Indecies of Messages and their size
                    CPMMI = { m:{ 'index':0, 'size':len(messages[m].content) } for m in messages }

                    # making cartesian product of children's messages and choosing the one with minimum cost
                    firstM = messages.keys()[0]
                    while CPMMI[firstM]['index'] < CPMMI[firstM]['size']:
                        sum_generators_outputs = sum([ self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators ])
                        sum_flows_children = sum([ messages[m].content[ CPMMI[m]['index'] ][0] for m in messages ])
                        sum_loads = sum(self.loads.values())
                        rFlow = sum_generators_outputs + sum_loads + sum_flows_children

                        # choosing minimum cost
                        if isFirst or abs(rFlow) < abs(minFlow):
                            minFlow = rFlow

                            sum_costs_generators = sum([ self.generators[g].domain()[ CPMGI[g]['index'] ] * self.generators[g].CI for g in self.generators ])
                            sum_costs_children = sum([ messages[m].content[ CPMMI[m]['index'] ][1] for m in messages ])
                            rCO = sum_costs_generators + sum_costs_children

                            minPowerCost = rCO
                            minPCState = tuple([ (m, messages[m].content[ CPMMI[m]['index'] ]) for m in messages ])
                            minGenerator = { g: self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators }
                            isFirst = False

                        for i in reversed(messages.keys()):
                            if CPMMI[i]['index'] < CPMMI[firstM]['size']:
                                CPMMI[i]['index'] += 1
                                if CPMMI[i]['index'] == CPMMI[i]['size']:
                                    if i != firstM:
                                        CPMMI[i]['index'] = 0
                                else:
                                    break

                    for i in reversed(self.generators.keys()):
                        if CPMGI[i]['index'] < CPMGI[i]['size']:
                            CPMGI[i]['index'] += 1
                            if CPMGI[i]['index'] == CPMGI[i]['size']:
                                if i != firstG:
                                    CPMGI[i]['index'] = 0
                            else:
                                break
            else:
                # Cartesian Product Matrix columns Indecies of Messages and their size
                CPMMI = { m:{ 'index':0, 'size':len(messages[m].content) } for m in messages }

                # making cartesian product of children's messages and choosing the one with minimum cost
                firstM = messages.keys()[0]
                while CPMMI[firstM]['index'] < CPMMI[firstM]['size']:
                    sum_flows_children = sum([ messages[m].content[ CPMMI[m]['index'] ][0] for m in messages ])
                    sum_loads = sum(self.loads.values())
                    rFlow = sum_loads + sum_flows_children

                    # choosing minimum cost
                    if isFirst or abs(rFlow) < abs(minFlow):
                        minFlow = rFlow

                        sum_costs_children = sum([ messages[m].content[ CPMMI[m]['index'] ][1] for m in messages ])
                        rCO = sum_costs_children

                        minPowerCost = rCO
                        minPCState = tuple([ (m, messages[m].content[ CPMMI[m]['index'] ]) for m in messages ])
                        minGenerator = { g: self.generators[g].domain()[ CPMGI[g]['index'] ] for g in self.generators }
                        isFirst = False

                    for i in reversed(messages.keys()):
                        if CPMMI[i]['index'] < CPMMI[firstM]['size']:
                            CPMMI[i]['index'] += 1
                            if CPMMI[i]['index'] == CPMMI[i]['size']:
                                if i != firstM:
                                    CPMMI[i]['index'] = 0
                            else:
                                break

            self.prevFinalResult = self.finalResult
            self.finalResult = (minFlow, minPowerCost, minGenerator)
            flowCO = (minFlow, minPowerCost)
            self.OPCStates[flowCO] = minGenerator

            if self.debugLevel >= 1:
                print "Final result in root node:"
                print "rFlow: ",minFlow, ", minPowerCost: ", minPowerCost, ", minGenerator: ",minGenerator

            self.propagateValueToChildren(minPCState)

            self.saveGeneratorsStates(minGenerator)
        else:
            if self.parent in messages:
                optimalFlowCO = messages[self.parent].content
                self.prevFinalResult = self.finalResult
                self.finalResult = (optimalFlowCO[0], optimalFlowCO[1], self.OPCStates[optimalFlowCO])
                if not self.isLeaf():
                    self.propagateValueToChildren(self.PCStates[optimalFlowCO])

                if self.debugLevel >= 1:
                    print "Final result in node ",self.id, ":"
                    print "rFlow: ",optimalFlowCO[0], ", minPowerCost: ", optimalFlowCO[1], ", minGenerator: ",self.OPCStates[optimalFlowCO]

            self.saveGeneratorsStates(self.OPCStates[optimalFlowCO])

    def propagateValueToChildren(self, messages):
        self.stateLog[-1]['sent'] = [ { 'to':m[0], 'content':str(m[1]) } for m in messages ]
        for m in messages:
            message = Message(self.id, m[0], m[1])

            if self.debugLevel >= 2:
                print "Message from node ",self.id," to child ",m[0],': ', m[1]

            self.powerGrid.grid[m[0]].messageBox.append(message)

    def isReady(self):
        if self.state == 1:
            if self.isLeaf():
                return True
            elif len(self.messageBox) == len(self.getChildren()):
                return True
            return False
        elif self.state == 2:
            if not self.isRoot():
                if len(self.messageBox) == 1:
                    if self.messageBox[0].sender == self.parent:
                        return True
                    else:
                        raise Exception('Error: Message from non parent in state 2.')
                elif len(self.messageBox) > 1:
                    raise Exception('Error: Invalid number of messages in state 2.')
        else:
            raise Exception('Error: Invalid state.')
        return False

    def run(self):
        if self.isReady():
            if self.state == 1:
                if self.isRoot():
                    self.propagateValues()
                    self.state = 1
                    self.update()
                else:
                    self.calculateValues()
                    self.state = 2
            elif self.state == 2:
                self.propagateValues()
                self.state = 1
                self.isFinished = True
                self.update()

    def reset(self):
        self.isFinished = False
        del self.stateLog[:]
        del self.learningStateLog[:]

    def saveGeneratorsStates(self, state):
        for g in state:
            self.generators[g].value = state[g]

    def capacityOfLineToParent(self):
        if not self.isRoot():
            return self.powerGrid.connections[(self.id, self.parent)]
        return sys.maxint

    def update(self):
        rlState = self.powerGrid.getRLState()
        print rlState
        if rlState['IsLearning']:
            if rlState['LearningInput'] == 'DCOP':
                # RL is learning form DCOP by mimicing
                if rlState['Actuator'] == 'DCOP':
                    if self.prevFinalResult != None:
                        qstate = self.getQStateOfResult(self.prevFinalResult)
                        reward = self.getReward(rlState)
                        nextQState = self.getQStateOfResult(self.finalResult)

                        self.qvalues[qstate] = (1-self.rl['alpha'])*self.qvalues[qstate] + self.rl['alpha']*(reward + self.rl['gamma']*self.qvalues[nextQState])
                # RL is acting and is learning rewards from DCOP by comparison
                else:
                    messages = self.readLearningMessageBox()
                    sum_resources = sum([ self.iResources[i].getValue() for i in self.iResources ])
                    sum_children = sum([ messages[m].content for m in messages ])
                    state = sum_resources + sum_children
                    action = self.policy(state)
                    qstate = (state, self.encodeAction(action))

                    nextState = state + action.values()
                    nextAction = self.policy(state)
                    nextQState = (nextState, self.encodeAction(nextAction))

                    # nextState is the flow to parent
                    reward = self.getReward(rlState, nextState)

                    self.qvalues[qstate] = (1-self.rl['alpha'])*self.qvalues[qstate] + self.rl['alpha']*(reward + self.rl['gamma']*self.qvalues[nextQState])

                    self.sendLearningMessageToParent(nextState)
                    self.learningResult = (state, action, nextState)
        # Learning is turned off
        else:
            messages = self.readLearningMessageBox()
            sum_resources = sum([ self.iResources[i].getValue() for i in self.iResources ])
            sum_children = sum([ messages[m].content for m in messages ])
            state = sum_resources + sum_children
            action = self.policy(state)

            nextState = state + action.values()

            self.sendLearningMessageToParent(nextState)
            self.learningResult = (state, action, nextState)

    def policy(self, state):
        maxQ = 0
        isFirst = True
        maxActions = []
        for a in list(self.actions):
            a = self.decodeAction(a)
            if isFirst or self.qvalues[(state, a)] > maxQ:
                maxQ = self.qvalues[(state, a)]
                del maxActions[:]
                maxActions.append(a)
                isFirst = False
            elif self.qvalues[(state, a)] == maxQ:
                maxActions.append(a)
        return random.choice(maxActions)

    def getReward(self, rlState, flow=None):
        if rlState['id'] == 0:
            return 1
        elif rlState['id'] == 1:
            if self.isLeaf():
                return 0
            # root or internal node
            else:
                return abs(flow) * -1.0
        return 0

    def getQStateOfResult(self, result):
        action = {}
        for g in result[2]:
            if not 'average_out' in self.powerGrid.generatorsJSON[g]:
                action[g] = result[2][g]
        self.actions.add(self.encodeAction(action))
        
        state = result[0] - sum(action.values())
        qstate = (state, self.encodeAction(action))
        return qstate

    def encodeAction(self, action):
        a = []
        for g in action:
            a.append(g)
            a.append(action[g])
        return tuple(a)

    def decodeAction(self, action):
        a = {}
        i = 0
        while i < len(action):
            a[action[i]] = action[i+1]
            i += 2
        return a

class Generator:
    def __init__(self, id, max_out, CI):
        self.id = id
        self.max_out = max_out
        self.CI = CI
        self.values = range(self.max_out + 1)
        self.value = None
        self.learningValue = None

    def domain(self):
        return self.values

class IntermittentResource:
    def __init__(self, id, average_out, sigma, prob, distribution):
        self.id = id
        self.average_out = average_out
        self.max_out = average_out
        self.sigma = sigma
        self.prob = prob
        self.CI = 0
        self.value = None
        self.learningValue = None
        self.distribution = distribution
        self.distributionIterator = 0
        self.maxIteration = len(distribution)

    def domain(self):
        # return [0, ran.normal(self.average_out, self.sigma)]
        #r = random.random()
        r = self.distribution[self.distributionIterator]
        self.distributionIterator += 1
        if self.distributionIterator == self.maxIteration:
            self.distributionIterator = 0
        if r < self.prob:
	       return [self.average_out]
        return [0]

    def getValue():
        return self.domain()[0]

class PowerGrid:
    def __init__(self, gridJSON, debugLevel=1):
        self.grid = {}
        self.connections = {}
        self.loads = {}
        self.generators = {}
        self.iResources = {}
        self.leaves = []
        self.levels = {}
        self.nodesJSON = gridJSON['nodes']
        self.loadsJSON = gridJSON['loads']
        self.generatorsJSON = gridJSON['generators']
        self.connectionsJSON = gridJSON['connections']
        self.distributions = gridJSON['distributions']
        self.debugLevel = debugLevel
        self.iteration = 0
        self.rl = gridJSON['options']
        self.learningStatesOrder = gridJSON['options']['order']
        # LearningInput, Actuator, IsLearning, Reward
        self.learningStates = [\
            {'id':0, 'LearningInput':'DCOP', 'Actuator':'DCOP', 'IsLearning':True, 'Reward':1},\
            {'id':1, 'LearningInput':'RL', 'Actuator':'RL', 'IsLearning':True, 'Reward':'|RL-DCOP|'},\
            {'id':2, 'LearningInput':'DCOP', 'Actuator':'RL', 'IsLearning':True, 'Reward':'|RL-DCOP|'},\
            {'id':3, 'LearningInput':'RL', 'Actuator':'RL', 'IsLearning':False, 'Reward':0}\
        ]
        self.initialize()

    def initialize(self):
        # Loads
        self.loads = self.loadsJSON

        # Generators
        for g in self.generatorsJSON:
            if 'average_out' in self.generatorsJSON[g]:
                self.generators[g] = IntermittentResource(g, self.generatorsJSON[g]['average_out'], self.generatorsJSON[g]['sigma'], self.generatorsJSON[g]['prob'], self.distributions[self.generatorsJSON[g]['distribution']])
                self.iResources[g] = self.generators[g]
            else:
                self.generators[g] = Generator(g, self.generatorsJSON[g]['max_out'], self.generatorsJSON[g]['CI'])

        children = set()
        nodes = set()
        for n in self.nodesJSON:
            nodes.add(n)
            if 'children' in self.nodesJSON[n]:
                if len(self.nodesJSON[n]['children']) == 0:
                    self.leaves.append(n)
                else:
                    for c in self.nodesJSON[n]['children']:
                        children.add(c)
            else:
                self.leaves.append(n)

        self.root = list(nodes - children)[0]
        if len(nodes - children) > 1:
            raise Exception('Error: More than one root found.')

        for n in self.nodesJSON:
            # looking for parent of node n
            parent = []
            for p in self.nodesJSON:
                if n in self.nodesJSON[p]['children']:
                    parent.append(p)

            if len(parent) > 1:
                raise Exception('Error: Graph is not acyclic.')

            if len(parent) == 1:
                parent = parent[0]
            else:
                parent = None

            iResources = []
            for g in self.nodesJSON[n]['generators']:
                if g in self.iResources:
                    iResources.append(g)

            self.grid[n] = Node(n, self.nodesJSON[n]['loads'], self.nodesJSON[n]['generators'], self, self.rl, iResources, parent, self.debugLevel)

        # connections thermal capacities
        for c in self.connectionsJSON:
            v1, v2 = c.split('-')
            self.connections[(v1,v2)] = self.connectionsJSON[c]
            self.connections[(v2,v1)] = self.connectionsJSON[c]

        self.setLevels()

        self.sumIterations = []
        sumIterations = 0
        for s in self.learningStatesOrder:
            sumIterations += s['numberOfIterations']
            self.sumIterations.append(sumIterations)

    def getRLState(self):
        for s in range(len(self.sumIterations)):
            if self.iteration <= self.sumIterations[s]:
                return self.learningStates[self.learningStatesOrder[s]['state']]
        return self.learningStates[3]

    def getChildren(self, nodeId):
        children = []
        if 'children' in self.nodesJSON[nodeId]:
            children = self.nodesJSON[nodeId]['children']
        return children

    def isLeaf(self, nodeId):
        return nodeId in self.leaves

    def isRoot(self, nodeId):
        return nodeId == self.root

    def setLevels(self):
        current_level_nodes = self.getChildren(self.root)
        self.levels = { g:None for g in self.grid }
        self.levels[self.root] = 0
        current_level = 1
        while len(current_level_nodes) > 0:
            children_level_nodes = []
            for p in current_level_nodes:
                self.levels[p] = current_level
                children = self.getChildren(p)
                for c in children:
                    self.levels[c] = current_level + 1
                    children_level_nodes.append(c)

            current_level += 1
            current_level_nodes = children_level_nodes

class Message:
    def __init__(self, sender, reciver, content):
        self.sender = sender
        self.reciver = reciver
        self.content = content
