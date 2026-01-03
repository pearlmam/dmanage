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

from dmanage.utils.utils import is_literal

defaultPyroFactoryHost = "localhost"
defaultPyroFactoryPort = 44444
defaultPyroFactoryName = "ProxyFactory"

######   server methods    #######
@Pyro5.api.expose
#@Pyro5.api.behavior(instance_mode="single",instance_creator=lambda Obj: create_instance(Obj,**kwargs))
class PyroFactory():
    def __init__(self):
        """setup rudimentary security? If someone gets access to Factory, 
        they can create any module they want, ensure no access to unwanted python modules"""
        self.secure = False
        
    def create_instance(cls,*args,**kwargs):
        obj = cls(*args,**kwargs)
        #obj.correlation_id = current_context.correlation_id
        return obj  
    
    def create(self,obj,module=None,**kwargs):
        print("Creating pyro object: '%s'..."%obj, end= ' ' )
        obj = get_object_from_module(obj,module)
        obj = pyroize_object(obj)
        obj = obj(**kwargs)
        uri = self._pyroDaemon.register(obj,force=True,weak=False)
        print("Done")
        obj.__register_components__()
        
        return uri


######### Pyro methods to inject   #######    

class Pyroize:
    """this is so pyro objects can register and monitor their own components as they are created"""
    _comp_uris = {}
    _pyroized = True
    
    @Pyro5.api.expose
    def __get_comp_uris__(self):
        return self._comp_uris
    @Pyro5.api.expose
    def __register_components__(self):
        comps = get_components(self)
        for name,comp in comps.items():
            if name not in self._comp_uris.keys():
                self._comp_uris[name] = self._register_component(comp)
        return self

    def _register_component(self,obj,onlyExposed=False,**kwargs):
        print("Registering Component: '%s'..."%obj, end= ' ' )
        if not onlyExposed:           
            obj = pyroize_object(obj) 
        else:
            print("cant create pyro object: '%s'..."%obj, end= ' ' )
            if not getattr(obj, '_pyroized',False):
                raise Exception("component is not pyroized and onlyExposed=True")
            if not getattr(obj, '_pyroExposed',False):
                raise Exception("component is not exposed and onlyExposed=True")
        if inspect.isclass(obj):
            obj= obj(**kwargs)   # instantiate the class, else it's already an instance
        
        uri = self._pyroDaemon.register(obj,force=True,weak=False)
        print("Done")
        obj.__register_components__()
        return uri
  
def pyroize_object(obj):
    """adds Factory methods and exposes object
    

    Parameters
    ----------
    obj : object or str
        Passing an Object to this will create an exposed Object.
        Passing a string will expose the object in the module
    module : module or str, optional
        If obj is an object, then no module is needed. 
        if obj is a string, module is where the object is
        The default is None.
        
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
    
    if inspect.isclass(obj):
        Obj = obj
    else:
        Obj = obj.__class__
    setattr(Obj, '_comp_uris', {})
    setattr(Obj, '__get_comp_uris__', Pyroize.__get_comp_uris__)
    setattr(Obj, '__register_components__', Pyroize.__register_components__)
    setattr(Obj, '_register_component', Pyroize._register_component)
    exposedObj = expose_all(obj)
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
    return obj     # should return input in case it's an instance, but I dont think anything needs to be returned


####### Client Methods  #########
class ProxyFactory():
    def __init__(self,uri="PYRO:ProxyFactory@localhost:44444"):
        self.Factory = Pyro5.api.Proxy(uri=uri)
    def create(self,obj,module=None,**kwargs):
        uri = self.Factory.create(obj,module=module,**kwargs)
        Obj = ProxyWrap(uri=uri)
        return Obj
    
class ProxyWrap():
    """Wraps a proxy so that component classes can be accessed"""
    def __init__(self,uri):
        self._proxy = Pyro5.api.Proxy(uri)
        self._comp_cache = {}       # dict of the created component proxies
        self._get_component_proxies()
        
        self._proxy_attrs = set(dir(self._proxy))
        self._comp_names = set(self._comp_cache)
        
    def _get_component_proxies(self):
        for name, uri in self._proxy.__get_comp_uris__().items():
            self._comp_cache[name] = ProxyWrap(uri)
        self._comp_names = set(self._comp_cache)
    
    def _register_components(self):
        self._proxy.__register_components__()
        self._get_component_proxies()
    
    def __dir__(self):
        return sorted(set(super().__dir__()) | self._comp_names | self._proxy_attrs)

    def __getattr__(self, name):
        """Changes the getattr behavior to access proxy components
        private methods of ProxyWrap are returned
        exposed class components of the proxy are returned as it's own proxy
        The shared object on the server must have __exposed_comps__ and __get_comp_uri__
        methods defined, see ExposeComps class in server.py/
        """

        if is_private_attribute(name):
            return getattr(self, name)        # return ProxyWrap attr
        elif name in self._comp_names:
            return self._comp_cache[name]     # return cached component
        else:
            return getattr(self._proxy,name)  # send proxy request
     
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

def get_components(obj):
    comps = {}
    for name,value in vars(obj).items():
        if is_private_attribute(name):
            continue
        if is_literal(value):
            continue
        if callable(value):
            continue
        if not hasattr(value, "__dict__"):
            continue
        comps[name] = value
    return comps

def get_object_from_module(obj,module):
    if type(obj) is str:
        if type(module) is str:   # should change to path-like
            moduleName = os.path.basename(module)
            # remove extention here
            sys.path.append(os.path.dirname(module))
            if moduleName not in sys.modules.keys():
                module = __import__(moduleName)             # load module
            else:
                module = reload(sys.modules[moduleName])    # must reload if already loaded
        elif isinstance(module,ModuleType):
            module=module
        else:
            raise Exception("Parameter 'module' must be a path or the module object")
        obj = getattr(module, obj)
    return obj


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
    #parser.add_argument("--use_ns", dest="use_ns", type=bool,default=False, help="to use a NameServer or not")
    options = parser.parse_args(args)
    Pyro5.api.serve({PyroFactory: defaultPyroFactoryName},host=options.host,
                    port=options.port, use_ns=False)
    
if __name__ == "__main__":
    main()
    
    