# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
import inspect
import Pyro5.api
from Pyro5.server import is_private_attribute
from dmanage.utils.objinfo import is_literal, is_pandas, has_immutable_base
from .serializers import URIHook


def is_exposable(obj):
    return not has_immutable_base(obj) and hasattr(obj, "__dict__")


def expose_all(obj):
    """ exposes all the class and bases
    Caveat: 
        
        This exposes ALL instances of the class, not just the returned one!
        classes are references and all instances reference it
        However, Proxies registering before exposing might not have access to 
        arrays even after exposing
    """
    Obj = obj if inspect.isclass(obj) else obj.__class__
    if is_exposable(Obj):
        Pyro5.api.expose(Obj)
    for base in Obj.__bases__:
        if is_exposable(base):
            expose_all(base)
    return obj


def _is_valid_component(name, value):
    if is_private_attribute(name) or callable(value):
        return False
    if is_literal(value) or is_pandas(value):
        return False
    return is_exposable(value)


def get_components(obj):
    return {
        name: val
        for name, val in inspect.getmembers(obj)
        if _is_valid_component(name, val)
    }


def get_attribute_names(obj):
    attrs = []
    for name in dir(obj):
        if name.startswith("__"):
            continue
        value = getattr(obj, name)
        if is_literal(value):
            attrs.append(name)
    return attrs


class Pyroize:
    """Mixin for objects so Proxies can access components and attributes."""
    _comp_uris = {}
    _pyroized = True
    _generated_uris = {}

    @Pyro5.api.expose
    def __get_comp_uris__(self):
        return self._comp_uris

    @Pyro5.api.expose
    def __register_components__(self):
        comps = get_components(self)
        for name, comp in comps.items():
            if name not in self._comp_uris:
                print(f"  Registering Component '{name}': '{comp}'...", end=" ")
                self._comp_uris[name] = self._register_component(comp)

    def _create_pyro_uri(self, obj, name=None):
        if name is None:
            name = obj.__name__ if inspect.isclass(obj) else type(obj).__name__

        if name in self._generated_uris:
            print(f"Object '{name}' already shared, 'reload=False': using cached uri")
            return URIHook(self._generated_uris[name])

        print(f"Creating pyro object: '{obj}'...", end=" ")
        obj = pyroize_object(obj)
        uri = str(self._pyroDaemon.register(obj, force=True, weak=False))
        print("Done")
        obj.__register_components__()
        self._generated_uris[name] = uri
        return URIHook(uri)

    def _register_component(self, obj, onlyExposed=False, **kwargs):
        if not onlyExposed:
            obj = expose_all(obj)
        else:
            if not getattr(obj, "_pyroized", False):
                raise Exception("Component is not pyroized and onlyExposed=True")
            if not getattr(obj, "_pyroExposed", False):
                raise Exception("Component is not exposed and onlyExposed=True")

        obj = pyroize_object(obj)
        if inspect.isclass(obj):
            obj = obj(**kwargs)

        uri = str(self._pyroDaemon.register(obj, force=True, weak=False))
        print("Done")
        obj.__register_components__()
        return uri

    @Pyro5.api.expose
    def __get_attribute_names__(self):
        return get_attribute_names(self)

    @Pyro5.api.expose
    def __get_attribute__(self, name):
        return getattr(self, name)


def pyroize_object(obj):
    """
    adds Factory arrays and exposes object
    

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
    Obj = obj if inspect.isclass(obj) else obj.__class__

    setattr(Obj, "_comp_uris", {})
    setattr(Obj, "_pyroized", True)
    setattr(Obj, "_generated_uris", {})

    setattr(Obj, "__get_comp_uris__", Pyroize.__get_comp_uris__)
    setattr(Obj, "__register_components__", Pyroize.__register_components__)
    setattr(Obj, "_register_component", Pyroize._register_component)
    setattr(Obj, "_create_pyro_uri", Pyroize._create_pyro_uri)

    setattr(Obj, "__get_attribute_names__", Pyroize.__get_attribute_names__)
    setattr(Obj, "__get_attribute__", Pyroize.__get_attribute__)
    return obj