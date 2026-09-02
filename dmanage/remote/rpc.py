# -*- coding: utf-8 -*-
try:
    import Pyro5.api
    from Pyro5.server import is_private_attribute
    import Pyro5.serializers
except ImportError:
    raise ImportError("Module 'Pyro5' must be installed to use the rpc package, use 'pip install dmanage[Pyro5]'")

from pathlib import Path
import pandas as pd
import subprocess as sp
import inspect
import time
import importlib.util
import dmanage.config
from dmanage.utils.objinfo import is_literal,is_pandas,has_immutable_base

defaultPyroFactoryHost = "localhost"
defaultPyroFactoryPort = 44444
defaultPyroFactoryName = "ProxyFactory"

script_dir = Path(__file__).parent.resolve()
rel_dir = Path('../../tests/helpers')
TEST_CONFIG_PATH =  script_dir / rel_dir / 'rpc_config.py'
TEST_PICKLE_CONFIG_PATH = script_dir / rel_dir / 'rpc_config_pickle.py'
TEMPLATE_CONFIG_PATH = script_dir / 'rpc_config.py'

__all__ = ["PyroFactory", "Pyroize", "ProxyFactory", "ProxyWrap"]

def client_ssh_setup(user,server,localPort=44444,remotePort=44444,verbose=False):
    """sets up ssh port forwarding on the client
    only needs to be run once. only needed to connect to remote hosts.
    ssh-L [LOCAL_PORT] : [REMOTE_HOST] : [REMOTE_PORT] user@server
    This opens [LOCAL_PORT], any connections go through ssh user@server
    and automatically connects to [REMOTE_HOST] : [REMOTE_PORT]
    note here REMOTE_HOST is always localhost 127.0.0.1, so it connects through ssh
    to the server and connects to the localhost.
    This way you can run the service on the local host and easily connect.
    Check if it worked with command "ss -ltn | grep [LOCAL PORT]"
    COPY THIS COMMAND:
    ssh -N -L 44444:127.0.0.1:44444 user@server
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

######   server arrays    #######
#@Pyro5.api.behavior(instance_mode="single", instance_creator=lambda clazz : clazz._create_instance(None))
@Pyro5.api.expose
class PyroFactory():
    """
    Factory to create pyro objects on a remote machine to connect to as a proxy
    create an rpc configuration file to  load into this factory. This config file
    sets rpc options and lists the allowed objects this factory can create.
    ONLY objects in that list can be created. The most common objects for this are
    DataUnits and DataGroups, you can generate DUs and DGs on the server as if
    they were local. An example config file is below:
        ::
            import Pyro5
            import sys
            from pathlib import Path
            import dmanage.config
            sys.path.insert(0, str(Path(__file__).parent.resolve()))
            from strata_objects import Parent,MyDataGroup,MyDataUnit,MyNewDataGroup,MyNewDataUnit

            ONLY_EXPOSED = False
            Pyro5.api.config.PICKLE_ENABLE = False # Enabling pickle is a massive security risk
            Pyro5.api.config.SERIALIZER = "serpent"# serpent,json?,pickle,dill
            dmanage.config.PARALLEL_BACKEND = "multiprocessing" # This is the local serializer used in multiprocessing, safe!

            EXPOSED_OBJECTS = {
                "Parent":Parent,
                "MyDataGroup":MyDataGroup,
                "MyDataUnit":MyDataUnit,
                "MyNewDataGroup":MyNewDataGroup,
                "MyNewDataUnit":MyNewDataUnit,
                }
    
    """
    
    config_path = None
    def __init__(self,configPath=None,parallel_backend=None):
        self.configPath=Path(configPath)
        if not self.configPath.exists():
            raise FileNotFoundError(f"Config file not found: {self.configPath}")
        self._load_config()
        self._pyro_uris = {}
        self.set_parallel_backend(parallel_backend)
    
    def _load_config(self,):
        spec = importlib.util.spec_from_file_location("custom_rpc_config", self.configPath)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        self._exposed_objects = getattr(config_module, "EXPOSED_OBJECTS", {})
        self.ONLY_EXPOSED = getattr(config_module, "ONLY_EXPOSED", {})
    
    def _get_object(self,name):
        if not name in self._exposed_objects:
            print(f"Failed! No object named '{name}'")
            raise Exception(f"No object named '{name}' is exposed to this factory")
        else:
            return self._exposed_objects[name]
    
    def get_exposed_object_list(self,):
        return list(self._exposed_objects.keys())
    
    def create(self,name,reload=False,args=(),kwargs={}):
        """
        reload can reuse uri or create new instance; however if a new instance 
        is created, the uri is no longer stored in self._pyro_uris. Pyro objects
        are cleaned up periodically when proxies are deleted... I think.
        """
        if name in self._pyro_uris and not reload:
            print("Object '%s' already shared, 'reload=False': using cached uri"%name)
            return self._pyro_uris[name]
        elif name in self._pyro_uris and reload:
            print("Object '%s' already shared, 'reload=True': recreating uri"%name)
        
        print("Creating pyro object: '%s'..."%name, end= ' ')
        obj = self._get_object(name)
        if not self.ONLY_EXPOSED:
            obj = expose_all(obj)
        obj = pyroize_object(obj)
        obj = obj(*args,**kwargs)
        uri = str(self._pyroDaemon.register(obj,force=True,weak=False))
        print("Done")
        obj.__register_components__()
        
        self._pyro_uris[name] = uri

        return uri
    
    def set_parallel_backend(self,backend=None):
        if backend:
            dmanage.config.PARALLEL_BACKEND = backend
            print(f"Parallel backend changed to '{backend}'")
            
    def get_parallel_backend(self):
        return dmanage.config.PARALLEL_BACKEND
    
    @classmethod    
    def _create_instance(cls,*args,**kwargs):
        if cls.config_path is None:
            raise ValueError("Config path has not been set.")
        obj = cls(*args,**kwargs)
        return obj 
    
######### Pyro arrays to inject   #######

class Pyroize:
    """Use with PyroWrap. Inherit from this so Proxies can access components and attributes"""
    _comp_uris = {}
    _pyroized = True
    _generated_uris={}
    
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
    
    def _create_pyro_uri(self,obj,name):
        
        if name is None:
            if inspect.isclass(obj):
                name = obj.__name__
            else:
                name = type(obj).__name__
                
        if name in self._generated_uris:
            print("Object '%s' already shared, 'reload=False': using cached uri"%name)
            return URIHook(self._generated_uris[name])
        
        print("Creating pyro object: '%s'..."%obj, end= ' ' )
        obj = pyroize_object(obj)
        uri = str(self._pyroDaemon.register(obj,force=True,weak=False))
        print("Done")
        obj.__register_components__()
        self._generated_uris[name]=uri
        uri = URIHook(uri)

        return uri
    
    # def _create_pyro_proxy(self,obj):
    #     print("Creating pyro object: '%s'..."%obj, end= ' ' )
    #     obj = pyroize_object(obj)
    #     uri = str(self._pyroDaemon.register(obj,force=True,weak=False))
    #     print("Done")
    #     obj.__register_components__()
    #     proxy = ProxyWrap(uri)
    #     return proxy
    
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
        
        uri = str(self._pyroDaemon.register(obj,force=True,weak=False))
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
    """adds Factory arrays and exposes object
    

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
    # internal attrs
    setattr(Obj, '_comp_uris', {})
    setattr(Obj, '_pyroized', True)
    setattr(Obj, '_generated_uris', {})
    
    # arrays
    setattr(Obj, '__get_comp_uris__', Pyroize.__get_comp_uris__)
    setattr(Obj, '__register_components__', Pyroize.__register_components__)
    setattr(Obj, '_register_component', Pyroize._register_component)
    setattr(Obj, '_create_pyro_uri', Pyroize._create_pyro_uri)
    #setattr(Obj, '_create_pyro_proxy', Pyroize._create_pyro_proxy)
    
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
        arrays even after exposing
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
    """
    Proxy connection to the PyroFactory on server
    This object lives on the client side as a Facade for the PyroFactory
    This enables more controll over the the interaction with the PyroFactory
    
    Its best to load this like this:
        ::
            from dmanage.remote.rpc import ProxyFactory
            # from myResearchProject.core import dataLevels as dl
            dl = ProxyFactory()
            DG = dl.DataGroup("path/to/datagroup")
            ...  process the data  ...
            
    This way your code is agnostic (almost) to whether data lives on 
    the locally or on the server; just uncomment one line 
        ::
            from dmanage.remote.rpc import ProxyFactory
            from myResearchProject.core import dataLevels as dl
            # dl = ProxyFactory()
            DG = dl.DataGroup("path/to/datagroup")
            ...  process the data  ...
            
    
    """
    def __init__(self,uri="PYRO:ProxyFactory@localhost:44444", proxy_reload=False):
        """Connect using uri of PyroFactory"""
        self.Factory = Pyro5.api.Proxy(uri=uri)
        self.exposed_objects = self.Factory.get_exposed_object_list()
        self._default_proxy_reload = proxy_reload
    
    def _sanitize_inputs(self, args, kwargs):
        """Clean and format inputs locally before sending over network."""
        # Example: Convert Path objects to strings for Serpent/JSON serialization
        clean_args = [str(a) if isinstance(a, Path) else a for a in args]
        clean_kwargs = {
            k: (str(v) if isinstance(v, Path) else v) 
            for k, v in kwargs.items()
        }
        return clean_args, clean_kwargs
    
    def create(self,name,*args,proxy_reload=None,**kwargs):
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
        # Pre-process inputs
        if proxy_reload is None:
            proxy_reload = self._default_proxy_reload
        clean_args, clean_kwargs = self._sanitize_inputs(args, kwargs)
        
        startTime = time.time()
        print("creating proxy for '%s'..."%name,end=' ')
        uri = self.Factory.create(name,reload=proxy_reload,args=clean_args,kwargs=clean_kwargs)
        Obj = ProxyWrap(uri=uri)
        executionTime = time.time() - startTime
        print("done in %0.2f seconds"%(executionTime))
        return Obj
    
    def set_parallel_backend(self,backend=None):
        self.Factory.set_parallel_backend(backend)
            
    def get_parallel_backend(self):
        return self.Factory.get_parallel_backend()
    
    def __getattr__(self, class_name: str):
        """Fallback for undefined attributes: intercepts class names and routes to self.create()."""
        def remote_constructor(*args, **kwargs):
            # Route directly through self.create to reuse timing and formatting logic
            return self.create(class_name, *args, **kwargs)
        return remote_constructor
    
class ProxyWrap():
    """
    Wraps a proxy so that component classes and attributes can be accessed
    This is recursive, so it should load all components of components
    
    """
    def __init__(self,uri):
        # print("ProxyWrap URI Type: %s"%type(uri))
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
    
    ###### metadata arrays to update proxy   ######
    def _register_components(self):
        self._proxy.__register_components__()
        self._get_component_proxies()
        
    def _get_attribute_names(self):
        self._proxy_attrs = self._proxy.__get_attribute_names__()
        
    ######   private dunder arrays
    def __dir__(self):
        return sorted(set(super().__dir__()) | 
                      self._comp_names | 
                      self._proxy_methods |
                      self._proxy_attrs)

    def __getattr__(self, name):
        """Changes the getattr behavior to access proxy components
        private arrays of ProxyWrap are returned
        exposed class components of the proxy are returned as it's own proxy
        The shared object on the server must have __exposed_comps__ and __get_comp_uri__
        arrays defined, see ExposeComps class in server.py/
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

#########  ProxyWrap/uri serialization hooks  ###########

URIHook = type('URIHook', (str,), {})   # URI class
## for serpent
def uri_to_dict(uri):
    data = str(uri)
    data = {'__class__':'URIDict','uri':data}
    return data

def dict_to_uri(classname,d):
    uri = str(d['uri'])
    proxyWrap = ProxyWrap(uri)
    return proxyWrap

Pyro5.api.register_class_to_dict(URIHook, uri_to_dict)
Pyro5.api.register_dict_to_class("URIDict", dict_to_uri)

## for pickle
def uri_to_proxy(uri):
    uri = str(uri)
    proxyWrap = ProxyWrap(uri)
    return proxyWrap

Pyro5.api.register_pickle_loads_hook("URIHook",uri_to_proxy)

#########  panda serialization hooks  ###########
orient='tight'
def df_to_dict(df):
    #print("DataFrame to dict")
    data = df.to_dict(orient=orient)
    data = {'__class__':'DataFrameDict','DataFrame':data}
    return data


def dict_to_df(classname, d):
    #print("dict to Dataframe")
    serializer = Pyro5.serializers.serializers[Pyro5.api.config.SERIALIZER]  # recreate any strange objects insode class
    data = serializer.recreate_classes(d['DataFrame'])
    data = pd.DataFrame.from_dict(data,orient=orient)
    #data = d['DataFrame']
    return data

def series_to_dict(series):
    #print("Series to dict")
    data = series.to_frame().to_dict(orient=orient)
    data = {'__class__':'SeriesDict','Series':data}
    return data

def dict_to_series(classname, d):
    #print("dict to Series")
    serializer = Pyro5.serializers.serializers[Pyro5.api.config.SERIALIZER]
    data = serializer.recreate_classes(d['Series'])
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
    """
    used to start PyroFactory from command line. call with dmanage-factory --config path/to/config.py
    """
    from argparse import ArgumentParser
    parser = ArgumentParser(description="D-Manage proxy factory command line launcher.")
    parser.add_argument("-n", "--host", dest="host",default='127.0.0.1', help="hostname to bind server on")
    parser.add_argument("-p", "--port", dest="port", type=int,default=defaultPyroFactoryPort, help="port to bind server on (0=random)")
    parser.add_argument("-c", "--config", dest="config",default=False, help="path to the configuration file")
    parser.add_argument("--test",action="store_true",help="Run in test mode using default test configurations")
    parser.add_argument("--test-pickle",action="store_true",help="Run the test with pickle enabled")
    parser.add_argument(
        "-b", "--parallel-backend",
        choices=["multiprocessing", "multiprocess"],
        default=None,
        help="Parallelization serializer backend (default: pickle)"
        )
    
    #parser.add_argument("--use_ns", dest="use_ns", type=bool,default=False, help="to use a NameServer or not")
    options = parser.parse_args(args)
    if not (options.test or options.config):
        config_path = Path(TEST_CONFIG_PATH)
        if config_path.exists():
            example_text = config_path.read_text(encoding="utf-8")
        else:
            example_text = "# Example config file not found on disk."

        parser.error(
            f"argument -c/--config is required unless --test is set.\n\n"
            f"--- Example config_rpc.py ---\n{example_text}\n"
            )

    if options.test:
        config_path = TEST_PICKLE_CONFIG_PATH if options.test_pickle else TEST_CONFIG_PATH
    else:
        config_path = options.config
        
    pyroFactory = PyroFactory(configPath=config_path,parallel_backend=options.parallel_backend)
    Pyro5.api.serve({pyroFactory: defaultPyroFactoryName},host=options.host,
                    port=options.port, use_ns=False)
    
if __name__ == "__main__":
    main()
    
    
