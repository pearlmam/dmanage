# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import dmanage.remote.rpc as rpc
from dmanage.remote.sync import rsync
import os
import time
import Pyro5.api
import Pyro5.server
import inspect

@Pyro5.api.expose
class Component():
    def __init__(self):
        self.attr = 'I am testing component attr access'
    def func(self):
        return 'random'

length = 100


def expose_attr(cls, name):
    """
    Adds a property to `cls` for attribute `name`.

    """
    storage = f"__prop__{name}"

    def getter(self):
        return getattr(self, storage)

    def setter(self, value):
        setattr(self, storage, value)

    def deleter(self):
        delattr(self, storage)

    prop = property(getter, setter, deleter)
    setattr(cls, name, prop)   

class MyDataUnit():
    classAttr = 'Im exposed'
    classComp = Component()
    def __init__(self,dataPath='path'):
        self.dataUnit = dataPath
        self.Component = Component()
    
    def __getattribute__(self, name):
        value = super().__getattribute__(name)
        return value
    def __setattr__(self, name,value):
        # if isinstance(value, Component):
            
        super().__setattr__( name,value)
        
    @Pyro5.api.expose
    class ClassComp():
        attr = 'I am a class attr'
        def func():
            return 'I am a class func'
        
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
    testtype = 'local'
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
    
    #exposedObj = Pyro5.api.expose(MyDataUnit)
    # result = Pyro5.server._get_exposed_members(MyDataUnit(),False)
    # print(result)
    # result = rsync(source = localProject,
    #          dest = remoteProject,
    #          dest_ssh = "%s@%s"%(user,host),
    #          verbose=False)
    

    Factory = rpc.get_remote_object(uri="PYRO:ProxyFactory@%s:44445"%host)
    # DD = Factory.create(obj,module=module,name='DataDir',dataPath=dataPath)
    DD = Factory.test()
    # DF = DD.gen_DataFrame()
    # print(DF)
    # array = DD.gen_numpy()
    # print(array)
    #Factory.create()

    # 
    # b = MyDataUnit('post expose')


    