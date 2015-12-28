from powergrid import PowerGrid
import json

class Scheduler:
    def __init__(self, powerGrid, stepByStep=False, debugLevel=1):
        self.pg = powerGrid
        self.stepByStep = stepByStep
        self.clock = 0
        self.terminated = False
        self.results = []
        self.episodesLog = []
        self.states = { n:set() for n in self.pg.grid }
        self.debugLevel = debugLevel

    def run(self):
        while not self.terminated:
            oneIsReady = False
            for node in self.pg.grid:
                n = self.pg.grid[node]
                if n.isReady():
                    oneIsReady = True
                    self.clock += 1
                    if self.debugLevel >= 1:
                        print
                        print "clock ",self.clock,": Node ",n.id," is running..."
                        print
                    n.run()
                    self.episodesLog.append({ 'node':node, 'state':n.stateLog[-1] })
                    if self.isFinished():
                        return
                    if self.stepByStep:
                        return
            if not oneIsReady:
                raise Exception('Error: No node is ready to run.')

    def isFinished(self):
        for c in self.pg.leaves:
            if not self.pg.grid[c].isFinished:
                return False
        self.terminated = True
        self.saveResults()
        for n in self.pg.grid:
            self.pg.grid[n].reset()
        return True

    def reset(self):
        self.terminated = False

    def saveResults(self):
        results = { 'connections' : [] }
        for n in self.pg.grid:
            parentId = self.pg.grid[n].parent
            if parentId != None:
                c = parentId + '-' + n
                if c in self.pg.connectionsJSON:
                    results['connections'].append( { 'id':c, 'value':self.pg.grid[n].finalResult[0], 'cap':self.pg.connectionsJSON[c], 'parent':parentId } )
                c = n + '-' + parentId
                if c in self.pg.connectionsJSON:
                    results['connections'].append( { 'id':c, 'value':self.pg.grid[n].finalResult[0], 'cap':self.pg.connectionsJSON[c], 'parent':parentId } )

        results['generators'] = [ { 'id':g, 'value':self.pg.generators[g].value, 'max_out':self.pg.generators[g].max_out } for g in self.pg.generators ]

        self.results.append(results)

        self.createStates()

    def writeResults(self):
        out = open('results.txt', 'w')

        edges = []
        for c in self.pg.connectionsJSON:
            v1, v2 = c.split('-')
            edges.append({ 'id': c, 'from': v1, 'to': v2, 'label': str(self.pg.connectionsJSON[c]) + ' kW', 'width': 3 })

        nodes = []
        for n in self.pg.grid:
            level = self.pg.levels[n]
            node = { 'id': n, 'label': n, 'group': 'node', 'level':level }
            nodes.append(node)
            for g in self.pg.grid[n].generators:
                if 'average_out' in self.pg.generatorsJSON[g]:
                    nodes.append({ 'id': g, 'label': g, 'group': 'intermittent', 'level':level+1 })
                else:
                    nodes.append({ 'id': g, 'label': g, 'group': 'generator', 'level':level+1 })
                edges.append({ 'from': n, 'to': g })
            for l in self.pg.grid[n].loads:
                nodes.append({ 'id': l, 'label': l+'='+str(self.pg.grid[n].loads[l])+' kW', 'group': 'load', 'level':level+1 })
                edges.append({ 'from': n, 'to': l })
        states = { n: [str(i) for i in list(self.states[n])] for n in self.states }

        output = { 'iterations': self.results, 'nodes': nodes, 'edges': edges, 'log': self.episodesLog, 'states': states }

        output['log'] = self.episodesLog
        output['states'] = states

        out.write(json.dumps(output, indent=4))
        out.close()

    def createStates(self):
        for n in self.pg.grid:
            gens = []
            for g in self.pg.grid[n].generators:
                if not 'average_out' in self.pg.generatorsJSON[g]:
                    gens.append(g)
            gensG = sum([self.pg.grid[n].generators[g].value for g in gens])
            self.states[n].add(str((self.pg.grid[n].finalResult[0], self.pg.grid[n].finalResult[2])))
