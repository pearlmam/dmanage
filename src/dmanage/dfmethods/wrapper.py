# -*- coding: utf-8 -*-

# for parallelize methods
import collections
import inspect
import itertools
from pathos.multiprocessing import Pool
import functools
import numpy as np
import pandas as pd


def looperize(func,concat=True):
    sig = inspect.signature(func)
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        DFs = []
        for step in args[0]:
            DFs = DFs + [func(step,*bound.args[1:],**bound.kwargs)]
        if concat:
            return pd.concat(DFs)
        else:
            return DFs
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

def parallelize_iterator_method(func,concat=True,ncPass=False):
    func = looperize(func,concat=concat)
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
        if not isinstance(steps,collections.abc.Iterable): steps = [steps]
        nc = min(nc,len(steps))   # dont use more cores than steps
        
        if nc>1:
            if type(steps) is range: steps=np.array(steps)
            stepss = np.array_split(steps, nc)
            variables = [(steps,)+bound.args[1:]+tuple(bound.kwargs.values()) for steps in stepss]
            pool = Pool(processes=nc)
            result = pool.starmap_async(func,variables)
            result.wait()
            DFs = result.get()
            pool.close()
            if concat:
                DFs = pd.concat(DFs)     # concat the list of DFs
            else:
                DFs = list(itertools.chain.from_iterable(DFs))  # make one list from list of lists
        else:
            DFs = func(steps,*args[1:],**kwargs)
        
        return DFs
    return wrapper




