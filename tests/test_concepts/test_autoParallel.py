#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from multiprocessing import Pool
import inspect

######################################
#    Simple Way
#####################################
def _mySum(numbers,method=0,nc=1):
    theSum = 0
    if method == 0:
        for number in numbers:
            theSum = theSum + number
    else:
        theSum = sum(numbers)
            
    return theSum
    
def mySum(numbers,method=0,nc=1):
    if nc>1:
        numbers = np.split(numbers, nc)
        variables = [(number,method) for number in numbers]
        pool = Pool(processes=nc)
        result = pool.starmap_async(_mySum,variables)
        result.wait()
        theSum = result.get()
        pool.close()
        theSum = _mySum(theSum)
    else: 
        theSum = _mySum(numbers)
    return theSum

numbers = np.linspace(0,100,100)
theSum = mySum(numbers,method=1,nc=4)
print(theSum)


################################
#    class way
################################

class serialFunctions():
    def __init__(self):
        self.classVar = 'class variable'
        
    def __init_subclass__(cls):
        cls.mySum = cls.paralellize(cls.mySum)
    
    def mySum(self,numbers,method=0,var0='var0 unused',var1='var1 unused',nc=1):
        theSum = 0
        if method == 0:
            for number in numbers:
                theSum = theSum + number
        else:
            theSum = sum(numbers)   
        print(var0)
        print(var1)
        print(self.classVar)
        return theSum
        
    def function2(variables):
        pass

class parallelFunctions(serialFunctions):
    def __init__(self):
        super().__init__()
        
    # code to make parallel versions for inhereted arrays
    def paralellize_v2(func):
        def wrapper(self,*args,**kwargs):
            # allInputVars = func.__code__.co_varnames[:func.__code__.co_argcount]
            # attempt to make arbitrary ordering of ags and kwargs okay.
            variables = ()
            for param in inspect.signature(func).parameters.values():
                if param.name == 'nc' and ('nc' in kwargs.keys()):
                    nc = param.default
                elif param.name in kwargs.keys():
                    variables = variables + (kwargs.pop(param.name),)
                elif not param.default is inspect._empty:
                    variables = variables + (param.default,)
            
            if nc>1:
                numbers = np.split(args[0], nc)
                variables = [(number,)+variables for number in numbers]
                pool = Pool(processes=nc)
                result = pool.starmap_async(func,variables)
                result.wait()
                results = result.get()
                pool.close()
                theResult = func(self,results,*kwargs.values())
            else: 
                theResult = func(self,args[0],*kwargs.values())
            return theResult
        return wrapper

    def paralellize(func):
        def wrapper(self,*args,**kwargs):
            nc = kwargs.pop('nc')
            if nc>1:
                numbers = np.split(args[0], nc)
                variables = [(number,)+tuple(kwargs.values()) for number in numbers]
                pool = Pool(processes=nc)
                result = pool.starmap_async(func,variables)
                result.wait()
                results = result.get()
                pool.close()
                theResult = func(self,results,*kwargs.values())
            else: 
                theResult = func(self,args[0],*kwargs.values())
            return theResult
        return wrapper
    pass
funcs = parallelFunctions()
theSum = funcs.mySum(numbers,method=1,var0='var0 used!',nc=1)
print('Sum Result: %f'%theSum)

def paralellize(func):
    def wrapper(*args,**kwargs):
        # first arg needs to be not kw, and kwargs need to be in order!!!
        # ??? make function more robust to input ordering
        nc = kwargs.pop('nc')
        if nc>1:
            numbers = np.split(args[0], nc)
            variables = [(number,)+tuple(kwargs.values()) for number in numbers]
            pool = Pool(processes=nc)
            result = pool.starmap_async(func,variables)
            result.wait()
            results = result.get()
            pool.close()
            theResult = func(results,*kwargs.values())
        else: 
            theResult = func(args[0],*kwargs)
        return theResult
    return wrapper

mySum = paralellize(_mySum)

theSum = mySum(numbers,method=1,var0='var0 used!',nc=4)
print('Sum Result: %f'%theSum)




