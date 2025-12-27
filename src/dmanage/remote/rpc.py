# -*- coding: utf-8 -*-

import Pyro5.api,Pyro5.nameserver
import Pyro5.errors
import Pyro5.socketutil
import socket

from types import ModuleType
import sys
import os
import pandas as pd
import warnings 
from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning)
    import paramiko
#from multiprocess import Process
from threading import Thread as Process

conda = 'dmanage'
    
def _getattr(self,attr):
    return getattr(self,attr)

def _setattr(self,attr):
    return setattr(self,attr)
    
class RPC():
    """
    not sure if needed
    """
    def __init__(self,server=None,user=None,conda=None):
        self.server = server
        self.user = user
        self.conda = conda
        self.conn=None
    
    def __del__(self):
        self.close()
    
    def close(self):
        self.nsLoop = False
        if hasattr(self, 'daemon'):
            self.daemon.close()
        if self.conn is not None:
            self.conn.close()
        
    def connect(self,):
        if self.server is not None and self.user is not None:
            self.conn = paramiko.SSHClient()	# setup the client variable
            # allow modification of host_key.  This is the local list of allowed connections
            self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())	
            self.conn.connect(self.server, username=self.user)
            # self.channel = self.conn.invoke_shell()
            # channel.send("print('hello') \n")
            # re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "",channel.recv(1024).decode("utf-8")).splitlines()
        else:
            self.conn = None
        return self.conn
    
    def nsLoopCondition(self):
        """way to kill the nameserver
        """
        return self.nsLoop
    
    
    def _start_nameserver(self,subProc=False):
        proc = None
        self.nsLoop = True
        kwargs = {'host':self.server,'loopCondition':lambda : self.nsLoopCondition()}
        if self.locate_ns() is None:
            if subProc:
                proc = Process(target=Pyro5.nameserver.start_ns_loop,kwargs=kwargs)
                proc.daemon = True    # this flag ensures thread is killed when terminal is closed
                proc.start()
            else:
                #Pyro5.nameserver.main()
                # hostname = socket.gethostname()
                #my_ip = Pyro5.socketutil.get_ip_address(None, workaround127=True)
                nameserverUri, nameserverDaemon, broadcastServer = Pyro5.nameserver.start_ns_loop(**kwargs)
                
        return proc
    
    def locate_ns(self):
        try:
            ns = Pyro5.api.locate_ns(self.server)
        except Pyro5.errors.NamingError:
            # print('No Naming Server')
            ns = None
        return ns
    
    def start_nameserver(self,subProc=False,debug=False):
        std = {}
        if self.conn is not None:
            commands = []
            if self.conda is not None:
                commands.append("conda activate %s"%(conda))
            commands.append("""python -c "import dmanage.remote.rpc as rpc""")
            commands.append("""rpc._start_nameserver(subProc=True)" """)
            
            command = ';'.join(commands)
            if debug:
                print(command)
            
            std['stdin'], std['stdout'], std['stderr'] = self.conn.exec_command(command, get_pty=True )
            if debug:
                for line in std['stdout'].readlines():
                    print(line)
                for line in std['stderr'].readlines():
                    print(line) 
        else:
            proc = self._start_nameserver(subProc=subProc)
            std['stdin'], std['stdout'], std['stderr']  = (None,None,None)
            
        return std
     
    def _create_pyro_object(self,obj,module=None,**kwargs):
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
        
        proc = Process(target=self.publish_pyro_object,args=(exposedInstance,))                   # start the event loop of the remote to wait for calls
        proc.daemon = True # this flag ensures thread is killed when terminal is closed
        proc.start()
        return proc
        #self.publish_pyro_object(exposedInstance)
        
    def publish_pyro_object(self,Obj,name='Obj'):
        self.daemon = Pyro5.server.Daemon()         # make a Pyro daemon
        uri = self.daemon.register(Obj)        # register the greeting maker as a Pyro object
        ns = self.locate_ns()             # find the name remote
        if ns is not None:
            ns.register(name, uri)            # register the object with a name in the name remote
        print(uri)
        print("Ready.")
        
        self.daemon.requestLoop()
        print('Request loop ended')
        return 
    
    def create_pyro_object(self,obj,module=None,debug=False,**kwargs):
        if not isinstance(obj,str) and self.conn is not None:
            raise Exception("Parameter 'obj' must be path-like object if the 'remote' is not localhost")
        elif not isinstance(module,str) and self.conn is not None:
            raise Exception("Parameter 'module' must be path-like object if the 'remote' is not localhost")
        std = {}
        if self.conn is not None:
            commands = []
            if self.conda is not None:
                commands.append("conda activate %s"%(conda))
            commands.append("""python -c "import dmanage.remote.rpc as rpc""")
        
            kwargsString = gen_kwargs_string(obj=obj,module=module,**kwargs)
            commands.append("""rpc._create_pyro_object('%s'),"""%(kwargsString))
            command = ';'.join(commands)
            if debug:
                print(command)
            
            std['stdin'], std['stdout'], std['stderr'] = self.conn.exec_command(command, get_pty=True )
            if debug:
                for line in std['stdout'].readlines():
                    print(line)
                for line in std['stderr'].readlines():
                    print(line) 
        else:
            self._create_pyro_object(obj,module=module,**kwargs)
            std['stdin'], std['stdout'], std['stderr'] = (None,None,None)
            
        return std
    
    def get_remote_object(self,name=None,uri=None):
        if name is not None:
            proxyString = "PYRONAME:%s"%name
        elif uri is not None:
            proxyString = "PYRO::%s"%uri
        
        Obj = Pyro5.api.Proxy(proxyString)
        return Obj
    
    def get_remote_daemon():
        return Pyro5.api.Proxy("PYRO:"+Pyro5.core.DAEMON_NAME+"@localhost:9090")
        
def create_instance(cls,dataPath,**kwargs):
    obj = cls(dataPath,**kwargs)
    #obj.correlation_id = current_context.correlation_id
    return obj

def gen_kwargs_string(**kwargs):
    kwargsString = ["%s='%s'"%(key,value) for key,value in kwargs.items()]
    ",".join(kwargsString)
    return kwargsString

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
    


