# -*- coding: utf-8 -*-

import Pyro5.api,Pyro5.nameserver
from types import ModuleType
import sys
import os
import pandas as pd
import warnings 
from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning)
    import paramiko

conda = 'dmanage'
    
def _getattr(self,attr):
    return getattr(self,attr)

def _setattr(self,attr):
    return setattr(self,attr)
    
class RPC():
    """
    not sure if needed
    """
    def __init__(self,obj,):
        self.obj = Pyro5.server.expose(obj)
        
    def start(self):
        # start the daemon on server
        Pyro5.api.daemon.register(self.obj)

def _start_nameserver():
    Pyro5.nameserver.main()
    
def start_nameserver(server=None,user=None):
    if server is not None and user is not None:
        command = """conda activate %s; """%(conda)+  \
                  """python -c "import dmanage.server.rpc as rpc; """ +  \
                  """rpc._start_nameserver()" """
        print(command)
        
        comp = paramiko.SSHClient()	# setup the client variable
        # allow modification of host_key.  This is the local list of allowed connections
        comp.set_missing_host_key_policy(paramiko.AutoAddPolicy())	
        comp.connect(server, username=user)
        stdin, stdout, stderr = comp.exec_command(command, get_pty=True )
        for line in stdout.readlines():
            print(line)
        for line in stderr.readlines():
            print(line) 
    else:
        Pyro5.nameserver.main()

def publish_pyro_object(Obj,name='Obj',server='127.0.0.1'):
    daemon = Pyro5.server.Daemon()         # make a Pyro daemon
    ns = Pyro5.api.locate_ns()             # find the name server
    uri = daemon.register(Obj)             # register the greeting maker as a Pyro object
    ns.register(name, uri)   # register the object with a name in the name server
    print(uri)
    print("Ready.")
    daemon.requestLoop()                   # start the event loop of the server to wait for calls


def create_instance(cls,dataPath,**kwargs):
    obj = cls(dataPath,**kwargs)
    #obj.correlation_id = current_context.correlation_id
    return obj

def _create_pyro_object(obj,module=None,**kwargs):
    if type(obj) is str:
        if module is None:
            raise Exception("If 'obj' is a string, then 'module' must be defined")
        elif type(module) is str:   # should change to path-like
            moduleDir = os.path.dirname(module)
            moduleName = os.path.basename(module)
            sys.path.append(moduleDir)
            module = __import__(moduleName)
        elif isinstance(module,ModuleType):
            module=module
        else:
            raise Exception("Parameter 'module' must be a path or the module object")
            
        Obj = getattr(module, obj)
    else:
        Obj = obj
    
    setattr(Obj, 'getattr', _getattr)
    setattr(Obj, 'setattr', _setattr)
    #Pyro5.api.config.SERIALIZER = "marshal"
    Obj = Pyro5.api.behavior(instance_mode="single",instance_creator=lambda Obj: create_instance(Obj,**kwargs))(Obj)
    exposedInstance = Pyro5.api.expose(Obj)
    publish_pyro_object(exposedInstance)


def get_remote_object(name=None,uri=None,server=None):
    if name is not None:
        proxyString = "PYRONAME:%s"%name
    elif uri is not None:
        proxyString = "PYRO::%s"%uri
    
    Obj = Pyro5.api.Proxy(proxyString)
    return Obj

def create_pyro_object(obj,module=None,server=None,user=None,**kwargs):
    if not isinstance(obj,str) and server is not None:
        raise Exception("Parameter 'obj' must be path-like object if the 'server' is not localhost")
    elif not isinstance(module,str) and server is not None:
        raise Exception("Parameter 'module' must be path-like object if the 'server' is not localhost")
    if server is not None:
        command = """conda activate %s; """%(conda)+  \
                  """python -c "import dmanage.server.rpc as rpc; """ +  \
                  """rpc._create_pyro_object('%s',"""%(obj) +  \
                  """module='%s',"""%module
        kwargsString = ["%s='%s'"%(key,value) for key,value in kwargs.items()]
        kwargsString = ",".join(kwargsString) + """)" """
        command = command + kwargsString
        print(command)
        
        comp = paramiko.SSHClient()	# setup the client variable
        # allow modification of host_key.  This is the local list of allowed connections
        comp.set_missing_host_key_policy(paramiko.AutoAddPolicy())	
        comp.connect(server, username=user)
        stdin, stdout, stderr = comp.exec_command(command, get_pty=True )
        for line in stdout.readlines():
            print(line)
        for line in stderr.readlines():
            print(line) 
    else:
        _create_pyro_object(obj,module=module,**kwargs)
    
    
    
    
# register the special serialization hooks
orient='tight'
def df_to_dict(df):
    #print("DataFrame to dict")
    data = df.to_dict(orient=orient)
    data = {'__class__':'DataFrameDict','DataFrame':data}
    return data

def dict_to_df(classname, d):
    #print("dict to Dataframe")
    data = pd.DataFrame.from_dict(d['DataFrame'],orient=orient)
    return data

def series_to_dict(series):
    #print("Series to dict")
    data = series.to_frame().to_dict(orient=orient)
    data = {'__class__':'SeriesDict','Series':data}
    return data

def dict_to_series(classname, d):
    #print("dict to Series")
    data = pd.DataFrame.from_dict(d['Series'],orient=orient).iloc[:,0]
    return data

Pyro5.api.register_class_to_dict(pd.core.frame.DataFrame, df_to_dict)
Pyro5.api.register_dict_to_class("DataFrameDict", dict_to_df)
Pyro5.api.register_class_to_dict(pd.core.frame.Series, series_to_dict)
Pyro5.api.register_dict_to_class("SeriesDict", dict_to_series)

if __name__ == "__main__":
    pass
    


