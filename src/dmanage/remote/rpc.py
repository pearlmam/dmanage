# -*- coding: utf-8 -*-
# from Pyro5.api import Daemon, serve, expose, behavior, current_context
import Pyro5.api
from Pyro5.server import is_private_attribute

from pathlib import Path
import os
import sys
import pandas as pd
import subprocess as sp
import inspect
from types import ModuleType
from importlib import reload

from dmanage.utils.objinfo import is_literal,is_container,is_immutable,is_pandas,has_immutable_base

defaultPyroFactoryHost = "localhost"
defaultPyroFactoryPort = 44444
defaultPyroFactoryName = "ProxyFactory"

# global SECURE_LOCATION
# global RESTRICTED_LOCATIONS 
RESTRICTED_LOCATIONS = ['anaconda3',]
SECURE_LOCATIONS = [os.getenv("HOME"),]      # doesnt work for windows...
ONLY_EXPOSED = False

def set_secure_location(locs):
    """
    """
    if not is_container(locs):
        locs = [locs]
    global SECURE_LOCATIONS
    SECURE_LOCATIONS = list(locs)
    

    
def client_ssh_setup(user,server,localPort=44444,remotePort=44444,verbose=False):
    """sets up ssh port fowarding on the client
    only needs to be run once. only needed to connect to remote hosts.
    ssh-L [LOCAL_PORT] : [REMOTE_HOST] : [REMOTE_PORT] user@server
    This opens [LOCAL_PORT], any connections go through ssh user@server
    and automatically connects to [REMOTE_HOST] : [REMOTE_PORT]
    note here REMOTE_HOST is always localhost 127.0.0.1, so it connects through ssh
    to the server and connects to the localhost.
    This way you can run the service on the local host and easily connect.
    Check if it worked with command "ss -ltn | grep [LOCAL PORT]"
    COPY THIS COMMAND:
    ssh -N -L 44444:127.0.0.1:44444 ***REMOVED***@***REMOVED***.***REMOVED***.edu
    """

    portString = '%s:127.0.0.1:%s'%(localPort,remotePort)
    serverString = '%s@%s'%(user,server)
    command = ['ssh', '-f','-N', '-L', portString, serverString]
    if verbose:
        print(' '.join(command) )
    sp.Popen(command)
    

def client_ssh_close(localPort=44444,verbose=False):
    command = ['pkill','-f',"ssh.*%s:127.0.0.1"%localPort]
    #command = ['pgrep','-af',"ssh.*%s:127.0.0.1"%localPort]
    # command = ['ps','aux','|','grep','ssh']
    if verbose:
        print(' '.join(command) )
    sp.Popen(command)
    # for line in proc.stdout.readlines():
    #     print(line.decode('ascii').rstrip('\n'))

######   server methods    #######
@Pyro5.api.expose
@Pyro5.api.behavior(instance_mode="single", instance_creator=lambda clazz : clazz.create_instance(None))
class PyroFactory():
    def __init__(self,secureLoc=None):
        """setup rudimentary security? If someone gets access to Factory, 
        they can create any module they want, ensure no access to unwanted python modules"""
        # self.secureLoc=secureLoc
        self._secureLocs = SECURE_LOCATIONS
        self._restrictLocs = RESTRICTED_LOCATIONS
        
    def create(self,obj,module=None,**kwargs):
        # check if location is secure
        
        if any([Path(secureLoc) not in Path(module).parents for secureLoc in SECURE_LOCATIONS]):
            raise Exception("Insecure 'module' Location: '%s' is not in %s"%(module, SECURE_LOCATIONS))
        if any([str(restrictLoc) in Path(module).parts for restrictLoc in RESTRICTED_LOCATIONS]):
            raise Exception("Restricted 'module' Location: '%s' is in one of %s"%(module, RESTRICTED_LOCATIONS))
        print("Creating pyro object: '%s'..."%obj, end= ' ' )
        
        obj = get_object_from_module(obj,module)
        if not ONLY_EXPOSED:
            obj = expose_all(obj)
        obj = pyroize_object(obj)
        obj = obj(**kwargs)
        uri = self._pyroDaemon.register(obj,force=True,weak=False)
        print("Done")
        obj.__register_components__()
        
        return uri
    
    @classmethod    
    def create_instance(cls,*args,**kwargs):
        obj = cls(*args,**kwargs)
        #obj.correlation_id = current_context.correlation_id
        return obj 
    
######### Pyro methods to inject   #######    

class Pyroize:
    """Use with PyroWrap. Inherit from this so Proxies can access components and attributes"""
    _comp_uris = {}
    _pyroized = True
    
    #####  Component Access  #####
    @Pyro5.api.expose
    def __get_comp_uris__(self):
        return self._comp_uris
    
    @Pyro5.api.expose
    def __register_components__(self):
        # print("Scanning Object '%s'..."%self )
        comps = get_components(self)
        for name,comp in comps.items():
            if name not in self._comp_uris.keys():
                print("  Registering Component '%s': '%s'..."%(name,comp), end= ' ' )
                self._comp_uris[name] = self._register_component(comp)

    def _register_component(self,obj,onlyExposed=False,**kwargs):
        """Need way to access onlyExposed, Maybe CONFIG FILE"""
        # print("  Registering Component: '%s'..."%obj, end= ' ' )
        if not onlyExposed:           
            obj = expose_all(obj)
        else:
            if not getattr(obj, '_pyroized',False):
                raise Exception("component is not pyroized and onlyExposed=True")
            if not getattr(obj, '_pyroExposed',False):
                raise Exception("component is not exposed and onlyExposed=True")
        obj = pyroize_object(obj)
        
        if inspect.isclass(obj):
            obj= obj(**kwargs)   # instantiate the class, else it's already an instance
        
        uri = self._pyroDaemon.register(obj,force=True,weak=False)
        print("Done")
        obj.__register_components__()
        return uri
    
    ##### Attribute access  ######
    # possibly need some check here if this is what you want
    @Pyro5.api.expose
    def __get_attribute_names__(self):
        return get_attribute_names(self)
    
    @Pyro5.api.expose
    def __get_attribute__(self,name):
        return getattr(self,name)

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
    
    # possible check here if this is what you want
    setattr(Obj, '__get_attribute_names__', Pyroize.__get_attribute_names__)
    setattr(Obj, '__get_attribute__', Pyroize.__get_attribute__)
    return obj

def is_exposable(obj):
    return not has_immutable_base(obj) and hasattr(obj, '__dict__')

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
    if is_exposable(Obj):
        #print("exposing '%s'"%Obj.__name__)
        Pyro5.api.expose(Obj)    
    bases = Obj.__bases__
    for base in bases:
        if is_exposable(base): # not inspect.isroutine(base) and
            expose_all(base)
    return obj     # should return input in case it's an instance, but I dont think anything needs to be returned


####### Client Methods  #########
class ProxyFactory():
    """Proxy connection to the PyroFactory on server"""
    def __init__(self,uri="PYRO:ProxyFactory@localhost:44444"):
        """Connect using uri of PyroFactory"""
        self.Factory = Pyro5.api.Proxy(uri=uri)
    
    def create(self,obj,module=None,**kwargs):
        """create Proxy for object in file
    
        Parameters
        ----------
        obj : str,object
            if string: Name of the object to create Pyro object and connect to Proxy.
            else the object itself?? security issue if pickle?
        module : str, optional
            path to the module/file. The default is None.
        **kwargs : TYPE
            arguments for object instantiation.

        Returns
        -------
        Obj : ProxyWrap
            Proxy to the object.

        """
        
        uri = self.Factory.create(obj,module=module,**kwargs)
        Obj = ProxyWrap(uri=uri)
        return Obj
    
class ProxyWrap():
    """Wraps a proxy so that component classes and attributes can be accessed"""
    def __init__(self,uri):
        self._proxy = Pyro5.api.Proxy(uri)
        self._comp_cache = {}       # dict of the created component proxies
        self._get_component_proxies()
        
        self._proxy_attrs = set(self._proxy.__get_attribute_names__())
        self._proxy_methods = set(dir(self._proxy))
        self._comp_names = set(self._comp_cache)
        
    def _get_component_proxies(self):
        for name, uri in self._proxy.__get_comp_uris__().items():
            if name not in self._comp_cache:
                self._comp_cache[name] = ProxyWrap(uri)
        self._comp_names = set(self._comp_cache)
    
    def _get_proxy_attr(self,name):
        return self._proxy.__get_attribute__(name)
    
    ###### metadata methods to update proxy   ######
    def _register_components(self):
        self._proxy.__register_components__()
        self._get_component_proxies()
        
    def _get_attribute_names(self):
        self._proxy_attrs = self._proxy.__get_attribute_names__()
        
    ######   private dunder methods
    def __dir__(self):
        return sorted(set(super().__dir__()) | 
                      self._comp_names | 
                      self._proxy_methods |
                      self._proxy_attrs)

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
        elif name in self._proxy_attrs:
            return self._get_proxy_attr(name) # return proxy attribute
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


#########  Helper Functions  ###########

def get_components(obj):
    comps = {}
    for name,value in vars(obj).items():
        if is_private_attribute(name):
            continue
        if is_literal(value) or is_pandas(value):
            continue
        if callable(value):
            continue
        if not is_exposable(value):
            # excludes things like numpy arrays
            continue
        comps[name] = value
    return comps

def get_attribute_names(obj):
    attrs = []
    for name,value in vars(obj).items():
        if is_literal(value):
            attrs = attrs + [name]
            continue
    return attrs

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
    #data = d['DataFrame']
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
    parser.add_argument("-n", "--host", dest="host",default='127.0.0.1', help="hostname to bind server on")
    parser.add_argument("-p", "--port", dest="port", type=int,default=defaultPyroFactoryPort, help="port to bind server on (0=random)")
    #parser.add_argument("--use_ns", dest="use_ns", type=bool,default=False, help="to use a NameServer or not")
    options = parser.parse_args(args)
    Pyro5.api.serve({PyroFactory: defaultPyroFactoryName},host=options.host,
                    port=options.port, use_ns=False)
    
if __name__ == "__main__":
    main()
    
    