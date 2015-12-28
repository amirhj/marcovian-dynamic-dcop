import sys
def argparser():
    keys = {\
        '-i':{'readValue':True,'default':1, 'name':'iterations'},\
        '--debug':{'readValue':True,'default':1, 'name':'debugLevel'},\
        '-p':{'readValue':True,'default':8666, 'name':'port'},\
        '--step':{'readValue':False,'default':False, 'name':'stepByStep', 'binary': True},\
        '--convergence':{'readValue':False,'default':False, 'name':'convergence'},\
        '--gamma':{'readValue':True,'default':0.8, 'name':'gamma'},\
        '--alpha':{'readValue':True,'default':0.9, 'name':'alpha'},\
        '--epsilon':{'readValue':True,'default':0.1, 'name':'epsilon'},\
        '--temperature':{'readValue':True,'default':0.9, 'name':'temperature'},\
        '-d':{'readValue':True,'default':0.999, 'name':'decay'},\
        '--saveModel':{'readValue':True,'default':True, 'name':'saveModel'},\
        '--loadModel':{'readValue':True,'default':False, 'name':'loadModel'},\
        '-n':{'readValue':True,'default':4, 'name':'numberOfAgents'},\
        '-s':{'readValue':True,'default':'R', 'name':'schedulerAlgorithm'},\
        '-m':{'readValue':True,'default':5000, 'name':'maxsteps'},\
        '-u':{'readValue':True,'default':'boltzmann', 'name':'updateType'}\
        }
    i = 0
    values = {}
    val = None
    while i < len(sys.argv):
        key = sys.argv[i]
        if key in keys:
            if keys[key]['readValue']:
                i += 1
                values[keys[key]['name']] = sys.argv[i]
            else:
                values[keys[key]['name']] = keys[key]['default']

            if 'binary' in keys[key]:
                if keys[key]['binary']:
                    values[keys[key]['name']] = True
        else:
            val = key
        i += 1

    for key in keys:
        if keys[key]['name'] not in values:
            values[keys[key]['name']] = keys[key]['default']

    values['inputFile'] = val
    values['debugLevel'] = int(values['debugLevel'])

    return values
