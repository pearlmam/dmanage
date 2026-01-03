# -*- coding: utf-8 -*-
# from Pyro5.api import Daemon, serve, expose, behavior, current_context
import Pyro5.api
from Pyro5.server import is_private_attribute

import os
import sys
import pandas as pd
import subprocess as sp
import inspect

from types import ModuleType
from importlib import reload

defaultPyroFactoryHost = "localhost"
defaultPyroFactoryPort = 44444
defaultPyroFactoryName = "ProxyFactory"

######   server methods    #######
@Pyro5.api.expose
@Pyro5.server.behavior(instance_mode="single",instance_creator=lambda clazz :  create_instance(clazz,False,nshost=None))
class PyroFactory():
    def __init__(self,use_ns=False,nshost=None):
        self.nshost = nshost
        if use_ns:
            self.ns = locate_ns(nshost)   # if there is a NameServer, use it for creation
        else:
            self.ns = None

    def create(self,obj,module=None,name=None,**kwargs):
        Obj = create_pyro_object(obj,module=module,**kwargs)
        Obj = Obj(**kwargs)
        uri = self._pyroDaemon.register(Obj,objectId=name,force=True,weak=False)
        if self.ns is not None: 
            self.ns.register(name, uri)
        #Obj._pyrouri = uri
        return uri

@Pyro5.api.expose
class ExposeComps:
    """The functions here allow automatic proxy creation for component classes"""
    def __get_comp_proxy__(self,name):
        return __get_comp_proxy__(self,name)
    
    def __get_comp_uri__(self,name):
        return __get_comp_uri__(self,name)
    
@Pyro5.api.expose
def __get_comp_proxy__(self,name):
    """Creates a shared object from the component and returns the proxy"""
    Comp = getattr(self,name)
    Comp = create_pyro_object(Comp)
    self._pyroDaemon.register(Comp)   # autoproxy!
    return Comp

@Pyro5.api.expose
def __get_comp_uri__(self,name):
    """Creates a shared object from the component and returns the uri"""
    Comp = getattr(self,name)
    Comp = create_pyro_object(Comp)
    return self._pyroDaemon.register(Comp)  # uri



def create_instance(cls,*args,**kwargs):
    obj = cls(*args,**kwargs)
    #obj.correlation_id = current_context.correlation_id
    return obj

def create_pyro_object(obj,module=None,**kwargs):
    """Creates and publishes a Pyro object
    

    Parameters
    ----------
    obj : object or str
        Passing an Object to this will create an exposed Object.
        Passing a string will expose the object in the module
    module : module or str, optional
        If obj is an object, then no module is needed. 
        if obj is a string, module is where the object is
        The default is None.
        
    **kwargs : TYPE
        These are the keyword arguments used to instantiate the object 'obj'.

    Raises
    ------
    Exception
        if the inputs are incorrect.

    Returns
    -------
    exposedObj :  object 
        
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
            if moduleName not in sys.modules.keys():
                module = __import__(moduleName)
            else:
                module = reload(sys.modules[moduleName])
        elif isinstance(module,ModuleType):
            module=module
        else:
            raise Exception("Parameter 'module' must be a path or the module object")
            
        obj = getattr(module, obj)
    else:
        pass
    
    print("creating pyro object: '%s'..."%obj, end= ' ' )
    if inspect.isclass(obj):
        Obj = obj
    else:
        Obj = obj.__class__
            
    setattr(Obj, '__get_comp_proxy__', __get_comp_proxy__)
    setattr(Obj, '__get_comp_uri__', __get_comp_uri__)
    # setattr(Obj, 'getattr', _getattr)
    # setattr(Obj, 'setattr', _setattr)
    exposedObj = expose_all(obj)
    print("Done")
    return exposedObj

def expose_all(obj):
    """ exposes all the class and bases
    Caveat: 
        This exposes ALL instances of the class, not just the returned one!
        classes are references and all instances reference it
        However, Proxies registering before exposing might not have access to 
        methods even after exposing
    
    """
    if not inspect.isclass(obj):
        Obj = obj.__class__
    else:
        Obj = obj
    if not Obj.__name__ == 'object':
        #print("exposing '%s'"%Obj.__name__)
        Pyro5.api.expose(Obj)    
    bases = Obj.__bases__
    for base in bases:
        if not inspect.isroutine(base) and not base.__name__ == "object":
            expose_all(base)
    
    return obj
    
    
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
    
    except Pyro5.errors.NamingError:
        ns = None
    return ns



####### Client Methods  #########
class ProxyFactory():
    def __init__(self,uri="PYRO:ProxyFactory@localhost:44444"):
        self.Factory = get_remote_object(uri=uri)
    def create(self,obj,module=None,name=None,**kwargs):
        uri = self.Factory.create(obj,module=module,name=name,**kwargs)
        Obj = ProxyWrap(uri=uri)
        return Obj
    
def get_remote_object(name=None,uri=None,host=None,port=None):
    if uri is not None:
        proxyString = uri
    elif name is not None and port is not None:
        host =  host if host else 'localhost'
        proxyString = "PYRO:%s@%s:%s"%(name,host,port)
    elif name is not None:
        ns = locate_ns(host)
        if ns is None:
            raise Exception("There must be a NameServer with only 'name' is defined.")
        proxyString = "PYRONAME:%s"%name
    else:
        raise Exception("uri or 'name' and 'port' or 'name' must be defined")
    Obj = Pyro5.api.Proxy(proxyString)
    return Obj 

class ProxyWrap():
    """Wraps a proxy so that component classes can be accessed"""
    def __init__(self,proxy=None,uri=None):
        if proxy:
            self._proxy = proxy          # the proxy to be wrapped
        elif uri:
            self._proxy = Pyro5.api.Proxy(uri)
        else:
            raise Exception("Input 'proxy' or 'uri' must be defined")
        self._compProxies = {}       # dict of the created component proxies
    
    def __dir__(self):
        base = set(super().__dir__())
        try:
            components = set(self._compProxies.keys())
            parent_attrs = set(dir(self._proxy))
        except Exception:
            components = set()
            parent_attrs = set()
        return sorted(base | components | parent_attrs)

    def __getattr__(self, name):
        """Changes the getattr behavior to access proxy components
        private methods of ProxyWrap are returned
        exposed class components of the proxy are returned as it's own proxy
        The shared object on the server must have __exposed_comps__ and __get_comp_uri__
        methods defined, see ExposeComps class in server.py/
        """

        if is_private_attribute(name):
            return getattr(self, name)        # return ProxyWrap attr
        if name in self._compProxies.keys():
            return self._compProxies[name]    # return cached Component
        try:
            return getattr(self._proxy, name) # return Proxy function call
        except Exception:
            pass
        # its possibly a component
        uri = self._proxy.__get_comp_uri__(name)          
        compProxy = ProxyWrap(uri=uri)
        self._compProxies[name] = compProxy
        return compProxy
    
    
    # def __getattr__(self, name):
    #     """Changes the getattr behavior to access proxy components
    #     private methods of ProxyWrap are returned
    #     exposed class components of the proxy are returned as it's own proxy
    #     The shared object on the server must have __exposed_comps__ and __get_comp_uri__
    #     methods defined, see ExposeComps class in server.py/
    #     """

    #     if is_private_attribute(name):
    #         return getattr(self, name)
    #     if name in self._compProxies.keys():
    #         return self._compProxies[name]
    #     try:
    #         uri = self._proxy.__get_comp_uri__(name)
    #     except Exception:
    #         try:
    #             return getattr(self._proxy, name)
    #         except AttributeError:
    #             raise AttributeError(name)
    #     compProxy = ProxyWrap(uri=uri)
    #     self._compProxies[name] = compProxy
    #     return compProxy
    
    def __reduce__(self):
        raise TypeError(
            f"'{self.__class__.__name__}' objects are not picklable. "
            "Create a new facade inside each process."
            )
    def __copy__(self):
        raise TypeError(f"'{self.__class__.__name__}' cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError(f"'{self.__class__.__name__}' cannot be deep-copied")        

def client_setup(user,server,localPort=44444,remotePort=44444,):
    """sets up ssh port fowarding on the client
    only needs to be run once. only needed to connect to remote hosts.
    ssh-L [LOCAL_PORT] : [REMOTE_HOST] : [REMOTE_PORT] user@server
    This opens [LOCAL_PORT], any connections go through ssh user@server
    and automatically connects to [REMOTE_HOST] : [REMOTE_PORT]
    note here REMOTE_HOST is always localhost 127.0.0.1, so it connects through ssh
    to the server and connects to the localhost.
    This way you can run the service on the local host and easily connect.
    """
    portString = '%s:127.0.0.1:%s'%(localPort,remotePort)
    serverString = '%s@%s'
    command = ['ssh', '-L', portString, serverString]
    sp.Popen(command)


#########  Helper Functions  ###########
def _getattr(self,attr):
    return getattr(self,attr)

def _setattr(self,attr):
    return setattr(self,attr)

def gen_kwargs_string(**kwargs):
    kwargsString = []
    for key,value in kwargs.items():
        if type(value) is str:
            kwargsString.append("%s='%s'"%(key,value))
        else:
            kwargsString.append("%s=%s"%(key,value))
    kwargsString = ",".join(kwargsString)
    return kwargsString

#########  panda serialization hooks  ###########
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

Pyro5.api.config.SERIALIZER = "serpent"
Pyro5.api.register_class_to_dict(pd.core.frame.DataFrame, df_to_dict)
Pyro5.api.register_dict_to_class("DataFrameDict", dict_to_df)
Pyro5.api.register_class_to_dict(pd.core.frame.Series, series_to_dict)
Pyro5.api.register_dict_to_class("SeriesDict", dict_to_series)




##### Factory Starters    ########
def start_factory(name='ProxyFactory',host=None,port=44444, use_ns=False,loopCondition=lambda : True):
    daemon = Pyro5.api.Daemon(host, port)
    with daemon:
        uri = daemon.register(PyroFactory, name)
        print(uri)
        daemon.requestLoop(loopCondition=loopCondition)
def main(args=None):
    from argparse import ArgumentParser
    parser = ArgumentParser(description="D-Manage proxy factory command line launcher.")
    parser.add_argument("-n", "--host", dest="host", help="hostname to bind server on")
    parser.add_argument("-p", "--port", dest="port", type=int,default=defaultPyroFactoryPort, help="port to bind server on (0=random)")
    parser.add_argument("--use_ns", dest="use_ns", type=bool,default=False, help="to use a NameServer or not")
    options = parser.parse_args(args)
    Pyro5.api.serve({PyroFactory: defaultPyroFactoryName},host=options.host,
                    port=options.port, use_ns=options.use_ns)
    
if __name__ == "__main__":
    main()
    
    