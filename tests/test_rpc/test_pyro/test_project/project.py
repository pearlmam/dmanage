# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import dmanage.remote.rpc as rpc
from dmanage.remote.sync import rsync
import os

import Pyro5.api

length = 100
class MyDataUnit():
    def __init__(self,dataPath):
        self.dataUnit = dataPath
        
    def gen_DataFrame(self,variant=1):
        if variant == 1:
            data = pd.DataFrame({'A':1.2,'B':"I'm a string",'C':True,'D':[x for x in range(10)]})
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
        else: 
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
        else:
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
    testtype = 'remote'
    if testtype == 'local':
        dataPath = '/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_data/vsim_data/VDC-87.8e3/'
        localProject = '/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_rpc/test_pyro/test_project/'
        remoteProject = "/home***REMOVED***Documents/SimulationProjects/temp/syncedProject/"
        host='127.0.0.1'
        user='marcus'
    else:
        dataPath = '/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_data/vsim_data/VDC-87.8e3/'
        localProject = '/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_rpc/test_pyro/test_project/'
        remoteProject = "/home/***REMOVED***/Documents/SimulationProjects/temp/syncedProject/"
        host='***REMOVED***.***REMOVED***.edu'
        user='***REMOVED***'
       
    obj = 'MyDataUnit'
    
    #localModule = "/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_rpc/test_pyro/test_project/"
    module = os.path.join(remoteProject,"project")
    
    conda='dmanage'
    # NS = rpc.NameServer()
    # NS.start(subProc=True)
    # # NS.checkstatus()
    # # NS.stop()
    
    # PO = rpc.PyroObject(id=1)
    # PO.create_object(obj,module=module,subProc=False,dataPath=dataPath)
    # PO.start(subProc=True)
    
    # C = rpc.Client()
    # DD = C.get_remote_object('Obj')
    
    # Peer = rpc.RemotePeer(server=server,user=user,conda='dmanage')
    # Peer.Server.connect()
    # Peer.Server.debugLevel = 2
    
    # Peer = rpc.LocalPeer()
    
    
    
    # Peer.NameServer.start(subProc=True)
    # # # Peer.Server.debugLevel = 0
    # Peer.PyroObject.create_object(obj,module=module,dataPath=dataPath)
    # Peer.PyroObject.start(subProc=True)
    # DD = Peer.Client.get_remote_object(name='Obj')
    # Peer.stop()
    
    # excludes = ['*']
    # includes = ["*.py","*/"]
    # options = '-am'
    
    result = rsync(source = localProject,
             dest = remoteProject,
             dest_ssh = "%s@%s"%(user,host),
             verbose=False)
    
    # Factory = rpc.get_remote_object('ProxyFactory')
    Factory = rpc.get_remote_object(uri="PYRO:ProxyFactory@%s:44444"%host)
    DD = Factory.create(obj,module=module,name='DataDir',dataPath=dataPath)
    DF = DD.gen_DataFrame()
    print(DF)
    
    


    