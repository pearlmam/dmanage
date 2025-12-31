# -*- coding: utf-8 -*-
# from Pyro5.api import Daemon, serve, expose, behavior, current_context
import Pyro5.api


import os
import sys
import pandas as pd

from types import ModuleType
from importlib import reload

def create_instance(cls,*args,**kwargs):
    obj = cls(*args,**kwargs)
    #obj.correlation_id = current_context.correlation_id
    return obj

######   server methods    #######
@Pyro5.api.expose
@Pyro5.server.behavior(instance_mode="single",instance_creator=lambda clazz :  create_instance(clazz,False,nshost=None))
class ProxyFactory():
    def __init__(self,use_ns=False,nshost=None):
        self.nshost = nshost
        if use_ns:
            self.ns = locate_ns(nshost)   # if there is a NameServer, use it for creation
        else:
            self.ns = None

    def create(self,obj,module=None,name=None,**kwargs):
        Obj = create_object(obj,module=module,**kwargs)
        Obj = Obj(**kwargs)
        uri = self._pyroDaemon.register(Obj,objectId=name,force=True,weak=False)
        if self.ns is not None: 
            self.ns.register(name, uri)
        return Obj
    
def create_object(obj,module=None,**kwargs):
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
            
        Obj = getattr(module, obj)
    else:
        Obj = obj
    
    setattr(Obj, 'getattr', _getattr)
    setattr(Obj, 'setattr', _setattr)
    
    exposedObj = Pyro5.api.expose(Obj)
    return exposedObj
    

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
        # for key in ns.list().keys():
        #     ns.remove(key)
        
    except Pyro5.errors.NamingError:
        # print('No Naming Server')
        ns = None
    return ns


####### Client Methods  #########
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

def get_proxy_factory(uri="PYRO:ProxyFactory@localhost:44444"):
    """Get the factory by uri
    
    To Do: I should probably register the uri somewhere so I can generate it automatically here
    """
    return get_remote_object(uri=uri)


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

def main(args=None):
    from argparse import ArgumentParser
    parser = ArgumentParser(description="D-Manage proxy factory command line launcher.")
    parser.add_argument("-n", "--host", dest="host", help="hostname to bind server on")
    parser.add_argument("-p", "--port", dest="port", type=int,default=44444, help="port to bind server on (0=random)")
    parser.add_argument("--use_ns", dest="use_ns", type=bool,default=False, help="to use a NameServer or not")
    options = parser.parse_args(args)
    Pyro5.api.serve({ProxyFactory: "ProxyFactory"},host=options.host,
                    port=options.port, use_ns=options.use_ns)
    
if __name__ == "__main__":
    main()
    
    