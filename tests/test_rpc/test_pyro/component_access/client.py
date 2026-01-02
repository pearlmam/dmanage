# -*- coding: utf-8 -*-

import Pyro5.api
from Pyro5.server import is_private_attribute
from functools import update_wrapper
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
        
    def __getattribute__(self, name):
        """Changes the getattr behavior to access proxy components
        private methods of ProxyWrap are returned
        exposed class components of the proxy are returned as it's own proxy
        The shared object on the server must have __exposed_comps__ and __get_comp_uri__
        methods defined, see ExposeComps class in server.py/
        """
        if is_private_attribute(name):
            return super().__getattribute__(name)    # returns ProxyWrap attr
        # get proxy and list of comps
        proxy = super().__getattribute__('_proxy')
        comps = proxy.__exposed_comps__()
        compProxies = super().__getattribute__('_compProxies')
        if name in comps:
            # generate new proxy on the fly, or get cached one.
            if name in compProxies.keys():
                return compProxies[name]
            else:
                compProxy = ProxyWrap(proxy.__get_comp_proxy__(name))
                self._compProxies.update({name: compProxy})
                return compProxy
        else:
            return getattr(proxy,name)

port = 44444
host = 'localhost'
name = 'MyClass'

myClass = ProxyWrap(uri="PYRO:%s@%s:%s"%(name,host,port))   

print(myClass.func())
print(myClass.Comp.func())
print(myClass.Comp.Comp.func())



