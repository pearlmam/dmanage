# -*- coding: utf-8 -*-

import collections
import pandas as pd

def is_iterable(obj):
    if isinstance(obj,collections.abc.Iterable) and not isinstance(obj, str) and not isinstance(obj,pd.core.frame.DataFrame):
        return True
    else:
        return False


class add_attribute:
    """Decorator that adds an attribute to a function without wrapping or renaming it."""
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __call__(self, func):
        setattr(func, self.name, self.value)
        return func
   
def child_override(func):
    """Decorator to mark a method as an override for a method."""
    add_attr = add_attribute('_override',True)
    return add_attr(func)
   
    
    
if __name__ == "__main__":
    # @add_attribute('_override',True)
    # def test():
    #     pass
    
    @child_override
    def test():
        pass
    print(test)
    print(test._override)
    pass
