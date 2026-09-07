#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  9 17:35:18 2025

@author: marcus
"""

import numpy as np
# from multiprocessing import Pool
from pathos.multiprocessing import Pool
import functools
import inspect

def parallelize(func):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        if 'nc' in kwargs.keys():
            nc = kwargs.pop('nc')
        else:
            nc = 1
        
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        
        
        values = bound.args[0]
        nc = min(nc,len(values))
        
        if nc>1:
            valuess = np.split(values, nc)
            variables = [(values,)+bound.args[1:]+tuple(bound.kwargs.values()) for values in valuess]
            pool = Pool(processes=nc)
            result = pool.starmap_async(func,variables)
            result.wait()
            values = result.get()
            pool.close()
            values = np.concatenate(values)
        else:
            values = func(values,**kwargs)
        return values
    return wrapper

def looperize(func):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        values = np.empty(0)
        for value in bound.args[0]:
            values = np.append(values,func(value,*kwargs.values()))
        return values
    return wrapper
  
def doSomething(value):
    return abs(value)

def doSomethingLooped(values):
    valuesOut = np.empty(0)
    for value in values:
        valuesOut = np.append(valuesOut,abs(value))
    return valuesOut

if __name__ == "__main__":
    values = np.linspace(-100,100,10000)
    
    # one wrapper picklable
    doSomethingLooped = parallelize(doSomethingLooped)
    result = doSomethingLooped(values,nc=4)  # works!
    
    # two wrappers NOT picklable but dillable
    doSomething = looperize(doSomething)
    doSomething = parallelize(doSomething)
    result = doSomething(values,nc=1)  # Fails with multiprocessing bu NOT pathos.multiprocessing
    
    
    


