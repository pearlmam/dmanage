import inspect
import itertools
from pathos.multiprocessing import Pool
import functools
import numpy as np
from dmanage.utils.utils import isIterable


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
        if iteratorType is np.ndarray and isIterable(result[0]):
            result = np.array(result)
        return result
    return wrapper


def parallelize_looped_method(func,ncPass=False):
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
            #func(variables[0][0],variables[0][1],variables[0][2],variables[0][3],variables[0][4])
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
            if not isIterable(arg0): arg0 = [arg0]   # determine if it is an iterable and make it one
            nc = min(nc,len(arg0))
            print('Adding one to values using %i cores...'%(nc), end=' ')
            result = addOne(arg0,arg1,nc=nc)
            executionTime = (time.time()-startTime)
            print(' Done in %0.2f seconds'%(executionTime))
            return result
        else:
            return arg0

    values = [1,2,3,4]
    addOne(values,arg1=True,nc=4)
    
    print()
    
    
    