# -*- coding: utf-8 -*-

import collections
import pandas as pd

PRIMITIVES = (int, float, str, bool, type(None))
CONTAINERS = (list, dict, set, tuple)

def is_iterable(obj):
    return (isinstance(obj,collections.abc.Iterable) and 
            not isinstance(obj, str) and 
            not isinstance(obj,pd.core.frame.DataFrame))

def is_primitive(obj):
    return isinstance(obj, PRIMITIVES)

def is_container(obj):
    return isinstance(obj, CONTAINERS)

def is_literal(obj):
    return (is_primitive(obj) or is_container(obj))


if __name__ == "__main__":
    pass
