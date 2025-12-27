# -*- coding: utf-8 -*-

import Pyro5.api,Pyro5.nameserver

import pandas as pd
import numpy as np

def _getattr(self,attr):
    return getattr(self,attr)

def _setattr(self,attr):
    return setattr(self,attr)   

def start_nameserver():
    Pyro5.nameserver.main()
        
def gen_pyro_object(Obj,name='Obj'):
    daemon = Pyro5.server.Daemon()         # make a Pyro daemon
    ns = Pyro5.api.locate_ns()             # find the name remote
    uri = daemon.register(Obj)       # register the greeting maker as a Pyro object
    ns.register(name, uri)   # register the object with a name in the name remote
    print(uri)
    print("Ready.")
    daemon.requestLoop()                   # start the event loop of the remote to wait for calls
    return uri

def create_instance(cls,dataPath,**kwargs):
    obj = cls(dataPath,**kwargs)
    #obj.correlation_id = current_context.correlation_id
    return obj

length = 100
class Test():
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
    
# register the special serialization hooks
orient='tight'
def df_to_dict(df):
    print("DataFrame to dict")
    data = df.to_dict(orient=orient)
    data = {'__class__':'DataFrameDict','DataFrame':data}
    return data

def dict_to_df(classname, d):
    print("dict to Dataframe")
    data = pd.DataFrame.from_dict(d['DataFrame'],orient=orient)
    return data

def series_to_dict(series):
    print("Series to dict")
    print(series)

    data = series.to_frame().to_dict(orient=orient)
    data = {'__class__':'SeriesDict','Series':data}
    return data

def dict_to_series(classname, d):
    print("dict to Series")
    data = pd.DataFrame.from_dict(d['Series'],orient=orient).iloc[:,0]
    return data


Pyro5.api.register_class_to_dict(pd.core.frame.DataFrame, df_to_dict)
Pyro5.api.register_dict_to_class("DataFrameDict", dict_to_df)
Pyro5.api.register_class_to_dict(pd.core.frame.Series, series_to_dict)
Pyro5.api.register_dict_to_class("SeriesDict", dict_to_series)

if __name__ == "__main__":
    source = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/pythonProject/'
    dest = '/home***REMOVED***Documents/temp/syncedProject/'
    excludes = ['*']
    includes = ["*.py","*/"]
    options = '-am'
    server='127.0.0.1'

    # result = rsync(source=source,
    #          dest=dest,
    #          dest_ssh=remote,
    #          options=options,
    #          includes=includes,
    #          excludes=excludes)
    
    import sys
    import os
    module = "core/dataDir"
    obj = 'MyDataDir'
    data = '/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_data/vsim_data/VDC-87.8e3/'
    # kwargs = {'unitType':'dir', 'nc':1}
    kwargs = {}
    path = os.path.join(dest, module)
    pathDir = os.path.dirname(path)
    moduleName = os.path.basename(path)
    sys.path.append(pathDir)
    module = __import__(moduleName)
    
    #Obj = getattr(module, obj)
    Obj = Test
    setattr(Obj, 'getattr', _getattr)
    setattr(Obj, 'setattr', _setattr)
    #setattr(Obj, 'create_instance', create_instance)
    # Instance = Obj.create_instance(data,**kwargs)
    
    
    Instance = create_instance(Obj,data,**kwargs)
    
    # orient='series'
    # df = Instance.gen_DataFrame(variant=3)
    # dictionary = df.to_dict(orient=orient)
    # df1 = pd.DataFrame(dictionary)
    # # df1 = pd.DataFrame.from_dict(dictionary,orient=orient)
    # print(df)
    # print(dictionary)
    # print(df1)
    
    # orient='tight'
    # series = Instance.gen_Series(variant=1)
    # dictionary = series.to_frame().to_dict(orient=orient)
    # # series1 = pd.Series(dictionary)
    # series1 = pd.Series(pd.DataFrame.from_dict(dictionary,orient=orient)).iloc[:,0]
    # print(series)
    # #print(dictionary)
    # print(series1)    
    
    
    Pyro5.api.config.SERIALIZER = "marshal"
    Obj = Pyro5.api.behavior(instance_mode="single",instance_creator=lambda Obj: create_instance(Obj,data,**kwargs))(Obj)
    exposedInstance = Pyro5.api.expose(Obj)
    uri = gen_pyro_object(exposedInstance)
    


