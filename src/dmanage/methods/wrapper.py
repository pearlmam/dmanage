import inspect
import itertools

from multiprocess import Pool
import functools
import numpy as np
from dmanage.utils.objinfo import is_iterable


WRAPPER_TYPE = 'class'

if WRAPPER_TYPE == 'class':
    ##########################
    #    More pickleable
    #########################
    class looperize():
        def __init__(self, func,update_wrapper=True):
            self.func = func
            #self.sig = inspect.signature(func)
            if update_wrapper:
                self.__wrapped__ = func
                functools.update_wrapper(self, func)
        
        def __call__(self,*args,**kwargs):
            sig = inspect.signature(self.func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            result = []
            steps = bound.args[0]
            iteratorType = type(steps)
            for step in steps:
                result.append(self.func(step,*bound.args[1:],**bound.kwargs))
            if iteratorType is np.ndarray and is_iterable(result[0]):
                result = np.array(result)
            return result
    
    class parallelize_looped_method():
        def __init__(self,func,ncPass=False,update_wrapper=True):
            self.func = func
            self.ncPass = ncPass
            #self.sig = inspect.signature(func)
            if update_wrapper:
                self.__wrapped__ = func
                functools.update_wrapper(self, func)
            
        def __call__(self,*args,**kwargs):
            if not self.ncPass and 'nc' in kwargs.keys():
                nc = kwargs.pop('nc')
            else:
                nc=1
            # binds the args and kwargs to the wrapped function 
            # so that arg and kwarg ordering the input doesnt matter
            sig = inspect.signature(self.func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # first arg is the iterable, and if it's not, make it one
            steps = bound.args[0]
            if not is_iterable(steps): steps = [steps]
            iteratorType = type(steps)
            nc = min(nc,len(steps))   # dont use more cores than steps
            
            if nc>1:
                if type(steps) is range: steps=np.array(steps)
                stepss = np.array_split(steps, nc)
                variables = [(steps,)+bound.args[1:]+tuple(bound.kwargs.values()) for steps in stepss]
                pool = Pool(processes=nc)
                #func(variables[0][0],variables[0][1],variables[0][2],variables[0][3],variables[0][4])
                result = pool.starmap_async(self.func,variables)
                result.wait()
                result = result.get()
                pool.close()
                if is_iterable(result[0]):
                    if iteratorType is np.ndarray:
                        result = np.concatenate(result)
                    else:
                        result = list(itertools.chain.from_iterable(result))  # make one list from list of lists
            else:
                result = self.func(steps,*args[1:],**kwargs)
            
            return result
    
    class parallelize_iterator_method():
        def __init__(self,func,ncPass=False):
            self.func = looperize(func,update_wrapper=False)
            self.func = parallelize_looped_method(self.func,ncPass=ncPass,update_wrapper=False)
            self.__wrapped__ = func
            functools.update_wrapper(self, func)
        def __call__(self,*args,**kwargs):
            return self.func(*args,**kwargs)
else:
    ################   
    # Less picklable            
    #########################
    def looperize(func):
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
            if iteratorType is np.ndarray and is_iterable(result[0]):
                result = np.array(result)
            return result
        return wrapper
    
    
    def parallelize_looped_method(func,ncPass=False):
        """Make the function parallel
    
        Parameters
        ----------
        func : function
            looped function to be parallelized.
        ncPass : bool, optional
            To pass the nc parameter to the original function. This is useful if the original function is
            already parallel and it is more efficient to loop through and run that parallely. This parameter
            is useful for automated wrapping and choosing what kind of wrapping on the fly.
            The default is False.
    
        Returns
        -------
        TYPE
            DESCRIPTION.
    
        """
        
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
            if not is_iterable(steps): steps = [steps]
            iteratorType = type(steps)
            nc = min(nc,len(steps))   # dont use more cores than steps
            
            if nc>1:
                if type(steps) is range: steps=np.array(steps)
                stepss = np.array_split(steps, nc)
                variables = [(steps,)+bound.args[1:]+tuple(bound.kwargs.values()) for steps in stepss]
                pool = Pool(processes=nc)
                #func(variables[0][0],variables[0][1],variables[0][2],variables[0][3],variables[0][4])
                result = pool.starmap_async(func,variables)
                result.wait()
                result = result.get()
                pool.close()
                if is_iterable(result[0]):
                    if iteratorType is np.ndarray:
                        result = np.concatenate(result)
                    else:
                        result = list(itertools.chain.from_iterable(result))  # make one list from list of lists
            else:
                result = func(steps,*args[1:],**kwargs)
            
            return result
        return wrapper
    
    def parallelize_iterator_method(func,ncPass=False):
        """
        These methods are more generic to any iterator, the DF method wraps a concat capability.
        I should put these somewhere else.
        """
        func = looperize(func)
        return parallelize_looped_method(func,ncPass=ncPass)


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
    values = addOne(values,arg1=True,nc=1)
    
    print(values)

    
    