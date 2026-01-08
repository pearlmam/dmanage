# -*- coding: utf-8 -*-

# for parallelize methods

import inspect
from multiprocess import Pool
import functools
import numpy as np
import pandas as pd
from dmanage.utils.objinfo import is_iterable


# These Double wrapped methods are slow for some reason. I want to get it dont like this though so I can have concat wrappers?
from dmanage.methods.wrapper import looperize as _looperize
from dmanage.methods.wrapper import parallelize_looped_method as _parallelize_looped_method
from dmanage.methods.wrapper import  parallelize_iterator_method as _parallelize_iterator_method


WRAPPER_TYPE = 'funcs'

if WRAPPER_TYPE == 'class':
    ##########################
    #    More pickleable
    #########################
    
    class looperize:
        def __init__(self,func,concat=True):
            self.func = func
            self.concat = concat
            #functools.update_wrapper(self, func)
            
        def __call__(self,*args,**kwargs):
            func = _looperize(self.func)
            result = func(*args,**kwargs)
            if self.concat:
                result = pd.concat(result)
            return result
    
    class parallelize_looped_method:
        def __init__(self,func,concat=True,ncPass=False):
            self.func = func
            self.concat = concat
            self.ncPass = ncPass
            #functools.update_wrapper(self, func)
        def __call__(self,*args,**kwargs):
            func = _parallelize_looped_method(self.func)
            result = func(*args,**kwargs)
            if self.concat:
                result = pd.concat(result)
            return result
    
    class parallelize_iterator_method:
        def __init__(self,func,concat=True,ncPass=False):
            self.func = func
            self.concat = concat
            self.ncPass = ncPass
            #functools.update_wrapper(self, func)
            
        def __call__(self,*args,**kwargs):
            func = _parallelize_iterator_method(self.func,self.ncPass)
            result = func(*args,**kwargs)
            if self.concat:
                result = pd.concat(result)
            return result
    
    class parallelize_df_method:
        def __init__(self,func):
            self.func = func
            
            functools.update_wrapper(self, func)
        def __call__(self,*args,**kwargs):
            if 'nc' in kwargs.keys():
                nc = kwargs.pop('nc')
            else:
                nc=1
            sig = inspect.signature(self.func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            if nc>1:
                DFs = np.split(args[0], nc)
                variables = [(DF,)+bound.args[1:]+tuple(bound.kwargs.values()) for DF in DFs]
                pool = Pool(processes=nc)
                result = pool.starmap_async(self.func,variables)
                result.wait()
                DFs = result.get()
                pool.close()
                DF = pd.concat(DFs)
            else: 
                DF = self.func(args[0],*args[1:],**kwargs)
            return DF


else:
    ################   
    # Less picklable            
    #########################
    
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
        
    
    def parallelize_looped_method(func,concat=True,ncPass=False):
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
    
    def parallelize_iterator_method(func,concat=True,ncPass=False):
        """
        This method wraps an iterator method in a parallel for loop for dataframes
    
        """
        func = looperize(func,concat)
        func = parallelize_looped_method(func,concat,ncPass=ncPass)
        #func = _parallelize_iterator_method(func,ncPass)
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            result = func(*args,**kwargs)
            # if concat:
            #     result = pd.concat(result)
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
    
    import time
    def _addOne(arg0,arg1):
        if arg1:
            return arg0 + 1
        else:
            return arg0 
    
    def addOne(arg0,arg1,nc=1):
        addOne = parallelize_iterator_method(_addOne)
        startTime = time.time()
        if arg1:
            if not is_iterable(arg0): arg0 = [arg0]   # determine if it is an iterable and make it one
            nc = min(nc,len(arg0))
            print('Adding one to values using %i cores...'%(nc), end=' ')
            result = addOne(arg0,arg1,nc=nc)
            executionTime = (time.time()-startTime)
            print(' Done in %0.2f seconds'%(executionTime))
            return result
        else:
            return arg0

    values = [1,2,3,4]
    addOne(values,arg1=True,nc=1)
