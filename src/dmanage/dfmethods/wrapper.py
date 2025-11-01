# -*- coding: utf-8 -*-

# for parallelize methods

import inspect
import itertools
from pathos.multiprocessing import Pool
import functools
import numpy as np
import pandas as pd
import builtins

from dmanage.utils.utils import isIterable

def _looperize(func):
    """
    This method wraps an iterator method in a for loop

    Parameters
    ----------
    func : function
        This is the method to be loop wrapped. It must return a single object
    concat : bool, optional
        To concat the result at the end or not The default is True.

    Returns
    -------
    function
        wrapper iterator function

    """
    
    sig = inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        result = []
        steps = args[0]
        iteratorType = type(steps)
        for step in steps:
            result = result + [func(step,*bound.args[1:],**bound.kwargs)]
        if iteratorType is np.ndarray and isIterable(result[0]):
            result = np.array(result)
        return result
    return wrapper

def looperize(func,concat=True):
    """
    This method wraps an iterator method in a for loop for dataframes

    """
    func = _looperize(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        result = func(*args,**kwargs)
        if concat:
            result = pd.concat(result)
        return result
    return wrapper

def _parallelize_looped_method(func,ncPass=False):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        if not ncPass and 'nc' in kwargs.keys():
            nc = kwargs.pop('nc')
        else:
            nc=1
        # binds the args and kwargs to the wrapped function 
        # so that arg and kwarg ordering the input doesnt matter
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        
        # first arg is the iterable, and if it's not, make it one
        steps = bound.args[0]
        if not isIterable(steps): steps = [steps]
        iteratorType = type(steps)
        nc = min(nc,len(steps))   # dont use more cores than steps
        
        if nc>1:
            if type(steps) is range: steps=np.array(steps)
            stepss = np.array_split(steps, nc)
            variables = [(steps,)+bound.args[1:]+tuple(bound.kwargs.values()) for steps in stepss]
            pool = Pool(processes=nc)
            result = func(stepss[0],*bound.args[1:])
            result = pool.starmap_async(func,variables)
            result.wait()
            result = result.get()
            pool.close()
            if isIterable(result[0]):
                if iteratorType is np.ndarray:
                    result = np.concatenate(result)
                else:
                    result = list(itertools.chain.from_iterable(result))  # make one list from list of lists
        else:
            result = func(steps,*args[1:],**kwargs)
        
        return result
    return wrapper

def parallelize_looped_method(func,ncPass=False,concat=True):
    """
    This method wraps an iterator method in a parallel for loop for dataframes

    """
    func = _parallelize_looped_method(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        result = func(*args,**kwargs)
        if concat:
            result = pd.concat(result)
        return result
    return wrapper

def _parallelize_iterator_method(func,ncPass=False):
    """
    These methods are more generic to any iterator, the DF method wraps a concat capability.
    I should put these somewhere else.
    """
    func = _looperize(func)
    return _parallelize_looped_method(func,ncPass=ncPass)

def parallelize_iterator_method(func,ncPass=False,concat=True):
    """
    This method wraps an iterator method in a parallel for loop for dataframes

    """
    func = _parallelize_iterator_method(func,ncPass)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        result = func(*args,**kwargs)
        if concat:
            result = pd.concat(result)
        return result
    return wrapper

def parallelize_df_method(func):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        if 'nc' in kwargs.keys():
            nc = kwargs.pop('nc')
        else:
            nc=1
        # binds the args and kwargs to the wrapped function 
        # so that arg and kwarg ordering the input doesnt matter
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        if nc>1:
            DFs = np.split(args[0], nc)
            variables = [(DF,)+bound.args[1:]+tuple(bound.kwargs.values()) for DF in DFs]
            pool = Pool(processes=nc)
            result = pool.starmap_async(func,variables)
            result.wait()
            DFs = result.get()
            pool.close()
            DF = pd.concat(DFs)
        else: 
            DF = func(args[0],*args[1:],**kwargs)
        return DF
    return wrapper


if __name__ == "__main__":
    
    
    def _addOne(value):
        return value+1
    addOne = parallelize_iterator_method(_addOne,concat=False)
    a = np.array([1,2,3,4,5,6,7,8])
    
    result = addOne(a,nc=4)
    print(result)
    
    




