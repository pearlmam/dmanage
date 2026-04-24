# -*- coding: utf-8 -*-

import collections
import pandas as pd
import io
import inspect

PRIMITIVES = (int, float, str, bool, type(None))
CONTAINERS = (list, dict, set, tuple)

try:
    import tables
    FILES = (io.TextIOBase,tables.hdf5extension.File)
except:
    FILES = (io.TextIOBase,)


def is_iterable(obj):
    """probably not useful anymore, use is_container"""
    return (isinstance(obj,collections.abc.Iterable) and 
            not isinstance(obj, str) and 
            not isinstance(obj,pd.core.frame.DataFrame))


def is_primitive(obj):
    return isinstance(obj, PRIMITIVES)

def is_container(obj):
    return isinstance(obj, CONTAINERS)

def is_file(obj):
    return isinstance(obj, FILES)

def is_literal(obj):
    return isinstance(obj,PRIMITIVES+CONTAINERS)

def is_immutable(obj):
    """Anything inheriting from imutables should also be immutable, except 'object'"""
    return issubclass(obj,PRIMITIVES+CONTAINERS+FILES) or obj.__name__ == 'object'

def is_pandas(obj):
    return has_base(obj,pd.core.accessor.DirNamesMixin)

def has_immutable_base(obj):
    return has_base(obj,PRIMITIVES+CONTAINERS+FILES) or getattr(obj,'__name__',False)=='object'

def has_base(obj,clazz):
    if inspect.isclass(obj):
        return issubclass(obj,clazz)
    else:
        return isinstance(obj,clazz)

if __name__ == "__main__":
    pass
