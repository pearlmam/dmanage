# -*- coding: utf-8 -*-

# for parallelize methods

import inspect
from multiprocessing import Pool
import functools
import numpy as np
import pandas as pd
import dmanage.utils.objinfo as objinfo


from dmanage.methods.wrapper import looperize as _looperize
from dmanage.methods.wrapper import parallelize_looped_method as _parallelize_looped_method
from dmanage.methods.wrapper import  parallelize_iterator_method as _parallelize_iterator_method


WRAPPER_TYPE = 'class'

if WRAPPER_TYPE == 'class':
    ##########################
    #    More pickleable
    #########################
    
    class looperize:
        def __init__(self,func,concat=True,bind_func=None):
            self.func = _looperize(func,bind_func=bind_func)
            self.concat = concat
            if bind_func is None:
                bind_func = func
            self.__wrapped__ = bind_func
            functools.update_wrapper(self, bind_func)
            
        def __call__(self,*args,**kwargs):
            #print('looperize')
            result = self.func(*args,**kwargs)
            if self.concat:
                result = pd.concat(result)
            return result
    
    class parallelize_looped_method:
        def __init__(self,func,concat=True,ncPass=False,bind_func=None):
            self.func = _parallelize_looped_method(func,ncPass=ncPass,bind_func=bind_func)
            self.concat = concat
            if bind_func is None:
                bind_func = func
            self.__wrapped__ = bind_func
            functools.update_wrapper(self, bind_func)
        def __call__(self,*args,**kwargs):
            #print('parallelize_looped')
            result = self.func(*args,**kwargs)
            if self.concat:
                result = pd.concat(result)
            return result
    
    class parallelize_iterator_method:
        def __init__(self,func,concat=True,ncPass=False,bind_func=None):
            if bind_func is None:
                bind_func = func
            self.__wrapped__ = bind_func
            functools.update_wrapper(self, bind_func)
            self.func = looperize(func,concat=concat,bind_func=bind_func)
            self.func = parallelize_looped_method(self.func,concat=concat,ncPass=ncPass,bind_func=bind_func)
            #self.func = _parallelize_iterator_method(func,ncPass)
            self.concat = concat
            
        def __call__(self,*args,**kwargs):
            result = self.func(*args,**kwargs)
            # if self.concat:
            #     result = pd.concat(result)
            return result
    
    class parallelize_df_method:
        def __init__(self,func):
            self.func = func
            self.__wrapped__ = func
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
                DFs = np.split(bound.args[0], nc)
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
            if concat and objinfo.is_container(result):
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
            if concat and objinfo.is_container(result):
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
    def _make_df(arg0,arg1,nc=1):
        if arg1:
            return pd.DataFrame([arg0])
        else:
            return pd.DataFrame([1]) 
    
    def make_df(arg0,arg1,nc=1):
        make_df = parallelize_iterator_method(_make_df)

        return make_df(arg0,arg1,nc=nc)
    
    # def make_df(arg0,arg1,nc=1):
    #     make_df = looperize(_make_df)
    #     make_df = parallelize_looped_method(make_df)
    #     return make_df(arg0,arg1,nc=nc)
    values = [1,2,3,4]
    print(make_df(values,arg1=True,nc=4))
    
    
    
