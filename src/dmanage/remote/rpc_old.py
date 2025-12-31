# -*- coding: utf-8 -*-

import Pyro5.api,Pyro5.nameserver
import Pyro5.errors
import Pyro5.socketutil

import warnings
import shutil
import time
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
import threading

from pathlib import Path
 
def locate_ns(host=None):
    """Locates a nameserver
    
    Parameters
    ----------
    host : str, optional
        If host is None, it finds the nameserver on the localhost.
        If the host is defined, it finds the nameserver on the host ip address
        The default is None.

    Returns
    -------
    ns : Pyro.NameServer
        returns a Pyro.NameServer object if found, else None.

    """
    try:
        ns = Pyro5.api.locate_ns(host)
        # remove presumbadly stale objects
        for key in ns.list().keys():
            ns.remove(key)
        
    except Pyro5.errors.NamingError:
        # print('No Naming Server')
        ns = None
    return ns

class Daemon():
    def __init__(self,id):
        
        self.id = id
        self.tempDir = Path('.dmanage/rpc/temp/')
        self.idLoc = Path.home() / self.tempDir
        self.idName = 'process'
        self.idFile = self.idLoc / ("process_id-%04d.pid"%self.id)
        self.proc = None
        self.started = False
        if not os.path.exists(self.idLoc):
            os.makedirs(self.idLoc)

    def start(self,target,subProc=False,args=(),kwargs={}):
        self.started = True
        def _target(*args,**kwargs):
            """wrap target so after loop finisheds a stopped flag is raised"""
            target(*args,**kwargs)
            self.stopped()
        
        if self.isrunning():
            print('Stale thread possible...')
            self.stop()
            
        self.running()         
        if subProc is not False:
            self.proc = Process(target=_target,args=args,kwargs=kwargs)
            self.proc.daemon = True
            self.proc.start()
            # print(self.proc)
        else:
            _target(*args,**kwargs)
            
    def stop(self,):
        print('Stopping...', end=' ')
        timeCheck = 0.2       # seconds
        timeMax = 3           # seconds
        iterationsMax = timeMax/timeCheck
        with open(self.idFile,'w') as f:
            f.write('status = stopping')
        i = 0
        if isinstance(self.proc,threading.Thread):
            while self.proc.is_alive():
                time.sleep(timeCheck)   # wait until killed
                i+=1
                if i > iterationsMax:
                    raise Exception("The thread exists in memory, but thread is still alive...")
        else:
            # the process is rogue and waiting for thread to update status to stopped
            while not self.isstopped():
                time.sleep(timeCheck)   # wait until killed
                i+=1
                if i > iterationsMax:
                    print('No response, moving on.')
                    warnings.warn("No response from possible thread; it's probably stopped. This warning occurs if daemons are not properly stopped. Make sure to stop running daemons if possible, or run stopAll() when you are done with your session and have or don't want any running daemons.")
                    self.stopped()
                    
    def close(self):
        self.stop()
            
    def hardStop(self,looptime=3):
        self.stop()
        time.sleep(looptime) # wait a bit longer to ensure stale threads are stopped
    
    def stopAll(self,looptime=3):
        shutil.rmtree(self.idLoc)
        time.sleep(looptime)
        shutil.rmtree(self.idLoc)
        
    def stopped(self,):
        with open(self.idFile,'w') as f:
            f.write('status = stopped')
            
    def running(self):
        with open(self.idFile,'w') as f:
            f.write('status = running')
    
    def checkstatus(self):
        if os.path.exists(self.idFile):
            with open(self.idFile,'r') as f:
                for line in f:
                    if 'status' in line:
                        status = line.split('=')[-1].strip()
                        break
                    else:
                        status = 'stopped'
        else: 
            status = 'stopped'
        # print(status)
        # print(self.proc)
        return status 
    
    def isstopped(self):
        return (self.checkstatus() == 'stopped')
    
    def isrunning(self):
        return (self.checkstatus() == 'running')
    
    def loopCondition(self):
        """way to kill the daemon
        """
        return self.isrunning()

class NameServer(Daemon):
    def __init__(self):
        id = 9999                 # this id is hard coded because only ONE ns can be running
        super().__init__(id)
        
        self.ip = Pyro5.socketutil.get_ip_address(None, workaround127=True)
     
    def start(self,subProc=False):
        """Starts a Pyro NameServer
        

        Parameters
        ----------
        broadcast : bool, optional
            If true, the NameServer can be accessed from clients. The default is False.
        subProc : bool or str, optional
            Whether to run on a thread or not. The default is False.
            If False, the method will hang here and run the NameServer loop
            If True, The NameServer loop will run on a thread, and not hang
            if 'regular', The NameServer loop will run on a regular thread instead of default daemon
            thread can be killed three ways: 
                1. if the thread is flagged as a daemon, closing the terminal will kill it
                2. Because threading uses shared memory, changing the self.nsLoop attribute
                to False will kill it.
                3. Use the self.close() method. This method will also kill a pyro object if created
        Returns
        -------
        proc : Thread object
            This currently isn't used, but you can control the thread with this object.
            This might be another way to kill the thread, but I currently don't use it.

        """
        ns = locate_ns()
        if ns is None:
            broadcast=False
            self.loop = True
            if broadcast:
                host = self.ip
            else:
                host=None
            kwargs = {'host':host,'loopCondition':lambda : self.loopCondition()}
            super().start(target=Pyro5.api.start_ns_loop,subProc=subProc,kwargs=kwargs)
        else:
            print('NameServer already started:\n%s'%ns)
    
    # this gets called when overwriting an instance, so I don't want to kill the nameserver
    # def __del__(self):
    #     print('garbage')
    #     self.stop()
    
    def stop(self):
        """close NameServer
        """
        super().stop()
        self.loop = False
        
class PyroObject(Daemon):
    def __init__(self,id=1):
        super().__init__(id)

    def start(self,subProc=False):
        super().start(target=self.publish_object,subProc=subProc,args=(self.exposedObj,))
        
        
    def create_object(self,obj,module=None,subProc=False,**kwargs):
        """Creates and publishes a Pyro object
        

        Parameters
        ----------
        obj : object or str
            Passing an Object to this will publish that object for RPC.
            Passing a string will publish the object in the module with this name
            The string input is useful for true remote operation because passing
            an object through ssh is challenging
        module : module or str, optional
            If the a true object is passed in 'obj', then no module is needed. 
            If an actual module object is passed, and obj is a string, then 
            the 'obj' string designates the name of the object in the module.
            If module is a str, the module will be loaded and 'obj' designates 
            the name of the object in the module.
            The default is None.
        subProc : bool, optional
            Whether to run on a thread or not. The default is False.
            If False, the method will hang here and run the daemon loop
            If True, The daemon loop will run on a thread, and not hang
            if 'regular', The pyro daemon loop will run on a regular thread instead of default daemon
            thread can be killed three ways: 
                1. if the thread is flagged as a daemon, closing the terminal will kill it
                2. Because threading uses shared memory, self.pyroDaemon.close() will kill it
                3. Use the self.close() method. This method will also kill a NameServer if created
            
        **kwargs : TYPE
            These are the keyword arguments used to instantiate the object 'obj'.

        Raises
        ------
        Exception
            if the inputs are incorrect.

        Returns
        -------
        proc : Thread object or None
            This currently isn't used, but you can control the thread with this object.
            This might be another way to kill the thread, but I currently don't use it.

        To Do: obj and module should check for path-like objects
        To Do: obj and module should check for package like objects, maybe a try-catch?
        """
        
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
        
        #Pyro5.api.config.SERIALIZER = "serpent"
        Obj = Pyro5.api.behavior(instance_mode="single",instance_creator=lambda Obj: create_instance(Obj,**kwargs))(Obj)
        self.exposedObj = Pyro5.api.expose(Obj)
        return self.exposedObj

    def publish_object(self,Obj,name='Obj'):
        """Publishes a Pyro object
        This method is generally not used directly, self.create_pyro_object should be used
        This method hangs in a loop waiting for requests.

        Parameters
        ----------
        Obj : object
            The object to be published
        name : string, optional
            The name to register on the NameServer. The default is 'Obj'.
            If no NameServer is running, this is not used and the uri printed on
            the terminal must be used to access the object. 
        Returns
        -------
        None.

        """
        
        self.pyroDaemon = Pyro5.server.Daemon()         # make a Pyro daemon
        uri = self.pyroDaemon.register(Obj)        # register the greeting maker as a Pyro object
        ns = locate_ns()             # find the name remote
        if ns is not None:
            ns.register(name, uri)            # register the object with a name in the name remote
        print(uri)
        # print("Ready.")
        self.pyroDaemon.requestLoop(loopCondition=lambda : self.loopCondition())
        print('Request loop ended')
        return 
    
    # def __del__(self):
    #     self.close()
    
        
class Client():
    def __init__(self,server=None,user=None,conda=None):
        self.server = server
        self.user = user
        
    def get_remote_object(self,name=None,uri=None,server=None):
        if name is not None:
            proxyString = "PYRONAME:%s"%name
        elif uri is not None:
            proxyString = "PYRO::%s"%uri
        elif server is not None:
            proxyString = proxyString + "@%s:9090"%server
        Obj = Pyro5.api.Proxy(proxyString)
        return Obj
    
    def get_remote_daemon(self):
        return Pyro5.api.Proxy("PYRO:"+Pyro5.core.DAEMON_NAME+"@localhost:9090")
    
    def stop(self):
        """I forget how to disconnect
        """

    def close(self):
        self.stop()


class RemoteServer():
    def __init__(self,server='127.0.0.1',user=None,conda=None):
        self.server = server
        self.user = user
        self.conda = conda
        self.conn = None
        self.debugLevel = 0
        
    def connect(self,):
        self.conn = paramiko.SSHClient()	# setup the client variable
        # allow modification of host_key.  This is the local list of allowed connections
        self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())	
        self.conn.connect(self.server, username=self.user)
        
        # transport = self.conn.get_transport()
        # self.chan = transport.open_session()
        # self.chan.get_pty()
        # self.chan.exec_command("bash")
        
        # if a invoke channel is used
        # self.channel = self.conn.invoke_shell()
        # channel.send("print('hello') \n")
        # re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "",channel.recv(1024).decode("utf-8")).splitlines()
        
        return self.conn

    def start_nameserver(self,broadcast=None,subProc=False):
        std = {}
        if self.conn is None:
            raise Exception("No paramiko connection, use self.connect()")
        if subProc: subProc = 'regular'
        commands = []
        kwargsString = gen_kwargs_string(broadcast=broadcast,subProc=subProc)
        if self.conda is not None:
            commands.append("conda activate %s"%(self.conda))
        
        commands.append("""python -c "import dmanage.remote.rpc as rpc""")
        commands.append("""Serv = rpc.Server() """)
        commands.append("""Serv.start_nameserver(%s)" """%kwargsString)
        
        command = ';'.join(commands)
        
        # command = "bash -c 'python3 -u -m Pyro5.nameserver > /tmp/pyro_ns.log 2>&1 & echo $!'"
        # command = ("""conda activate dmanage> /tmp/pyro_ns.log 2>&1; """ 
        #            """python3  -c """
        #            """ "import paramiko; """
        #            """print('hello world')" """ 
        #            """>> /tmp/pyro_ns.log 2>&1 """
        #            """& echo $! """
        #           )
        if self.debugLevel > 0:
            print(command)
        
        stdin, stdout, stderr = self.conn.exec_command(command, get_pty=False )
        # ns_pid = int(stdout.read().decode().strip())
        # print('pid = %d'%ns_pid)
        if self.debugLevel > 1:
            for line in stdout.readlines():
                print(line)
            for line in stderr.readlines():
                print(line) 
        time.sleep(2)   # wait for Nameserver to start, need check here...
        return std
     
    def create_pyro_object(self,obj,module=None,subProc=False,**kwargs):
        std = {}
        if self.conn is  None:
            raise Exception("No paramiko connection, use self.connect()")
        if subProc: subProc = 'regular'
        commands = []
        kwargsString = gen_kwargs_string(obj=obj,module=module,subProc=subProc,**kwargs)
        if self.conda is not None:
            commands.append("conda activate %s"%(self.conda))
        commands.append("""python -c "import dmanage.remote.rpc as rpc""")
        commands.append("""Serv = rpc.Server() """)
        commands.append("""Serv.create_pyro_object(%s)" """%(kwargsString))
        command = ';'.join(commands)
        
        if self.debugLevel > 0:
            print(command)
        
        stdin, stdout, stderr = self.conn.exec_command(command, get_pty=False )
        if self.debugLevel > 1:
            for line in stdout.readlines():
                print(line)
            for line in stderr.readlines():
                print(line) 
        time.sleep(1)   # wait for object to start, need check here...
        return std
    
    def __del__(self):
        self.close()
    
    def close(self):
        if self.conn is not None:
            self.conn.close()

class LocalPeer():
    """This acts as both client and server on a local machine
    This is rudimentary, but might be able to pass information from server to client
    and vice versa. For example, it may pass the uri so a NameServer is not needed?
    """
    
    def __init__(self):
        self.PyroObject = PyroObject()
        self.NameServer = NameServer()
        self.Client = Client()
    
    def stop(self):
        self.NameServer.stop()
        self.PyroObject.stop()
        self.Client.stop()
        
    def close(self):
        self.stop()
    
class RemotePeer():
    def __init__(self,server=None,user=None,conda=None):
        self.Server = RemoteServer(conda=conda)
        self.Client = Client(server=server,user=user)
        
    def close(self):
        self.Server.close()
        self.Client.close()
    

#########  Helper Functions  ###########

def _getattr(self,attr):
    return getattr(self,attr)

def _setattr(self,attr):
    return setattr(self,attr)

def create_instance(cls,dataPath,**kwargs):
    obj = cls(dataPath,**kwargs)
    #obj.correlation_id = current_context.correlation_id
    return obj

def gen_kwargs_string(**kwargs):
    kwargsString = []
    for key,value in kwargs.items():
        if type(value) is str:
            kwargsString.append("%s='%s'"%(key,value))
        else:
            kwargsString.append("%s=%s"%(key,value))
    kwargsString = ",".join(kwargsString)
    return kwargsString

def print_threads():
    for thread in threading.enumerate(): 
        print(thread.name)



#########  register the special serialization hooks  ###########
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
    
    D = Daemon()
    D.createID(1)
    pass
    




