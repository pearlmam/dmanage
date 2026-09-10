# -*- coding: utf-8 -*-
import time
import subprocess as sp
from pathlib import Path
import Pyro5.api
from Pyro5.server import is_private_attribute

def client_ssh_setup(user, server, localPort=44444, remotePort=44444, verbose=False):
    """
    sets up ssh port forwarding on the client
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
    portString = f"{localPort}:127.0.0.1:{remotePort}"
    serverString = f"{user}@{server}"
    command = ["ssh", "-f", "-N", "-L", portString, serverString]
    if verbose:
        print(" ".join(command))
    sp.Popen(command)


def client_ssh_close(localPort=44444, verbose=False):
    command = ["pkill", "-f", f"ssh.*{localPort}:127.0.0.1"]
    if verbose:
        print(" ".join(command))
    sp.Popen(command)


class ProxyFactory:
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

    def __init__(self, uri="PYRO:ProxyFactory@127.0.0.1:44444", proxy_reload=False):
        self.Factory = Pyro5.api.Proxy(uri=uri)
        self.exposed_objects = self.Factory.get_exposed_object_list()
        self._default_proxy_reload = proxy_reload

    def _sanitize_inputs(self, args, kwargs):
        clean_args = [str(a) if isinstance(a, Path) else a for a in args]
        clean_kwargs = {
            k: (str(v) if isinstance(v, Path) else v) for k, v in kwargs.items()
        }
        return clean_args, clean_kwargs

    def create(self, name, *args, proxy_reload=None, **kwargs):
        """
        create Proxy for object in file
    
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
        if proxy_reload is None:
            proxy_reload = self._default_proxy_reload
        clean_args, clean_kwargs = self._sanitize_inputs(args, kwargs)

        startTime = time.time()
        print(f"Creating proxy for '{name}'...", end=" ")
        uri = self.Factory.create(
            name, reload=proxy_reload, args=clean_args, kwargs=clean_kwargs
        )
        Obj = ProxyWrap(uri=uri)
        print(f"Done in {time.time() - startTime:.2f} seconds")
        return Obj

    def set_parallel_backend(self, backend=None):
        self.Factory.set_parallel_backend(backend)

    def get_parallel_backend(self):
        return self.Factory.get_parallel_backend()

    def set_parallel_start_method(self, method=None):
        self.Factory.set_parallel_start_method(method)

    def get_parallel_start_method(self):
        return self.Factory.get_parallel_start_method()

    def __getattr__(self, class_name: str):
        def remote_constructor(*args, **kwargs):
            return self.create(class_name, *args, **kwargs)

        return remote_constructor


class ProxyWrap:
    """Wraps a Pyro proxy to allow recursive attribute and component access."""

    def __init__(self, uri):
        self._proxy = Pyro5.api.Proxy(uri)
        self._comp_cache = {}
        self._get_component_proxies()
        self._proxy_attrs = set(self._proxy.__get_attribute_names__())
        self._proxy_methods = set(dir(self._proxy))
        self._comp_names = set(self._comp_cache)

    def _get_component_proxies(self):
        for name, uri in self._proxy.__get_comp_uris__().items():
            if name not in self._comp_cache:
                self._comp_cache[name] = ProxyWrap(uri)
        self._comp_names = set(self._comp_cache)

    def _get_proxy_attr(self, name):
        return self._proxy.__get_attribute__(name)

    def _register_components(self):
        self._proxy.__register_components__()
        self._get_component_proxies()

    def _get_attribute_names(self):
        self._proxy_attrs = self._proxy.__get_attribute_names__()

    def __dir__(self):
        return sorted(
            set(super().__dir__())
            | self._comp_names
            | self._proxy_methods
            | self._proxy_attrs
        )

    def __getattr__(self, name):
        """
        Changes the getattr behavior to access proxy components
        private arrays of ProxyWrap are returned
        exposed class components of the proxy are returned as it's own proxy
        The shared object on the server must have __exposed_comps__ and __get_comp_uri__
        arrays defined, see ExposeComps class in server.py/
        """
        if is_private_attribute(name):
            return getattr(self, name)
        elif name in self._comp_names:
            return self._comp_cache[name]
        elif name in self._proxy_attrs:
            return self._get_proxy_attr(name)
        else:
            return getattr(self._proxy, name)

    def __reduce__(self):
        raise TypeError(
            f"'{self.__class__.__name__}' objects are not picklable. "
            "Create a new facade inside each process."
        )

    def __copy__(self):
        raise TypeError(f"'{self.__class__.__name__}' cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError(f"'{self.__class__.__name__}' cannot be deep-copied")