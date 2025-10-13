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

def parallelize(func):
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        nc = kwargs.pop('nc')
        values = args[0]
        nc = min(nc,len(values))
        
        if nc>1:
            valuess = np.split(values, nc)
            variables = [(values,)+tuple(kwargs.values()) for values in valuess]
            pool = Pool(processes=nc)
            result = pool.starmap_async(func,variables)
            result.wait()
            values = result.get()
            pool.close()
        else:
            # DFs = []
            # for step in steps:
            #     DFs = DFs + [func(step,*kwargs.values())]
            values = func(values,**kwargs)
        return np.concatenate(values)
    return wrapper

def looperize(func):
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        values = np.empty(0)
        for value in args[0]:
            values = np.append(values,func(value,*kwargs.values()))
        return values
    return wrapper
  
def doSomething(value,nc=1):
    return abs(value)

def doSomethingLooped(values,nc=1):
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
    result = doSomething(values,nc=4)  # Fails with multiprocessing bu NOT pathos.multiprocessing
    
    
    


