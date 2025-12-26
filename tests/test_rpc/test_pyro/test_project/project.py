# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import dmanage.server.rpc as rpc

length = 100
class MyDataUnit():
    def __init__(self,dataPath):
        self.dataUnit = dataPath
        
    def gen_DataFrame(self,variant=1):
        if variant == 1:
            data = pd.DataFrame({'A':1.2,'B':'Im a string','C':True,'D':[x for x in range(10)]})
        elif variant == 2:
            index = np.linspace(0,100,length)
            values = index*2
            data = pd.DataFrame({'current':values},index=index)
            data.index.name = 'voltage'
        elif variant == 3:
            time = np.linspace(0,100,length)
            x = np.linspace(0,1,length)
            X,T = np.meshgrid(x,time)
            voltage = -X**2+0.5+T
            data = pd.DataFrame(voltage,columns=x,index=time)
            data.columns.name = 'x'
            data.index.name = 'Time'
            data = data.stack()
            data.name = 'voltage'
            data = pd.DataFrame(data)
        elif variant == 4:
            time = np.linspace(0,100,length)
            x = np.linspace(0,1,length)
            X,T = np.meshgrid(x,time)
            voltage = -X**2+0.5+T
            current = (-X**2+0.5+T)*1000
            data = pd.DataFrame(voltage,columns=x,index=time)
            data.columns.name = 'x'
            data.index.name = 'Time'
            data = data.stack()
            data.name = 'voltage'
            data = pd.DataFrame(data)
        return data
    
    def gen_Series(self,variant=1):
        if variant == 1:
            time = np.linspace(0,100,length)
            x = np.linspace(0,1,100)
            X,T = np.meshgrid(x,time)
            voltage = -X**2+0.5+T
            data = pd.DataFrame(voltage,columns=x,index=time)
            data.columns.name = 'x'
            data.index.name = 'Time'
            data = data.stack()
            data.name = 'voltage'
        elif variant == 2:
            time = np.linspace(0,100,length)
            x = np.linspace(0,1,100)
            X,T = np.meshgrid(x,time)
            voltage = -X**2+0.5+T
            data = pd.DataFrame(voltage,columns=x,index=time)
            data.columns.name = 'x'
            data.index.name = 'Time'
            data = data.stack()
            data.name = 'voltage'
        return data
    
    def gen_dict(self):
        data = {'A':1.2,'B':'Im a string','C':True,'D':[x for x in range(10)]}
        return data
    
    def gen_numpy(self,):
        data = np.linspace(0,10,100)
        # data = {'A':data}
        return data
    
    
    
if __name__ == "__main__":
    dataPath = '/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_data/vsim_data/VDC-87.8e3/'
    obj = 'MyDataUnit'
    module = "/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_rpc/test_pyro/test_project/project"
    server='127.0.0.1'
    user='marcus'
    # rpc.start_nameserver(server=server,user=user)
    rpc.create_pyro_object(obj,module=module,server=server,user=user,dataPath=dataPath)
    #rpc._create_pyro_object('MyDataUnit',module='/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_rpc/test_pyro/test_project/project',dataPath='/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_data/vsim_data/VDC-87.8e3')
    