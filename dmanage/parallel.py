import inspect
import itertools
import warnings
from concurrent.futures import ThreadPoolExecutor
import functools
import numpy as np
from dmanage.utils.objinfo import is_iterable
import sys
import atexit

##### Setup backend for Pool, checks config for which backend
import dmanage.config
from multiprocessing import Pool as StandardPool
try:
    from multiprocess import Pool as DillPool
    HAS_MULTIPROCESS = True
except ImportError:
    DillPool = None
    HAS_MULTIPROCESS = False

_BACKENDS = {
    "multiprocess": DillPool,
    "dill": DillPool,                  # Alias for convenience
    "multiprocessing": StandardPool,
    "pickle": StandardPool,            # Alias for convenience
}

def Pool(*args, **kwargs):
    backend_key = getattr(dmanage.config, "PARALLEL_BACKEND", "multiprocessing")
    if backend_key in ("dill", "multiprocess") and not HAS_MULTIPROCESS:
        warnings.warn(
            f"Parallel backend '{backend_key}' requested, but the 'multiprocess' package "
            "is not installed. Falling back to standard 'multiprocessing'.",
            RuntimeWarning
            )
        return StandardPool(*args, **kwargs)
    pool_cls = _BACKENDS.get(backend_key, StandardPool)
    return pool_cls(*args, **kwargs)
__all__ = ["ReusablePool", "looperize", "parallelize_looped_method", "parallelize_iterator_method"]

class ReusablePool:
    """
    This method is useful to create one global pool instance for double 
    parallel wrapped methods with ncPass=True. This creates a global pool
    in the first wrap for the second wrap to use in its parallel calls.
    This reduces the pool allocation cost per method, but also fixes some 
    strange issues when using double wrapping and RPC. 
    """
    
    _instance = None
    _nc = None
    _backend = None
    _lock_count = 0

    @classmethod
    def get_pool(cls, nc):
        current_backend = getattr(dmanage.config, "PARALLEL_BACKEND", "multiprocessing")
        
        # Works for both multiprocessing and multiprocess without extra imports
        is_alive = cls._instance is not None and getattr(cls._instance, '_state', None) == 'RUN'
    
        if not is_alive or cls._nc != nc or cls._backend != current_backend:
            if cls._instance is not None:
                try:
                    cls._instance.close()
                    cls._instance.join()
                except Exception:
                    pass
            
            cls._instance = Pool(processes=nc)
            cls._nc = nc
            cls._backend = current_backend
    
        return cls._instance

    @classmethod
    def close(cls, force=False):
        if cls._instance is not None and (cls._lock_count == 0 or force):
            try:
                cls._instance.close()
                cls._instance.join()
            except Exception:
                pass
            cls._instance = None
            cls._nc = None
            cls._backend = None

    @classmethod
    def lock(cls):
        cls._lock_count += 1

    @classmethod
    def unlock(cls):
        cls._lock_count = max(0, cls._lock_count - 1)
atexit.register(lambda: ReusablePool.close(force=True))

WRAPPER_TYPE = 'class'
# WRAPPER_TYPE = 'funcs'

def split_range(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def split_integer(a, n):
    k, m = divmod(a, n)
    return ( (i*k+min(i, m),(i+1)*k+min(i+1, m) ) for i in range(n))

def split_integer2(a, n):
    k, m = divmod(a, n)
    return [ ( (i+1)*k+min(i+1, m)) - (i*k+min(i, m)) for i in range(n) ]

if WRAPPER_TYPE == 'class':
    ##########################
    #    More pickleable
    #########################
    class looperize():
        """
        wrapper functor to make iterator methods looped. Generally used in conjucntion
        with `parallelize_looped_method`
        """
        def __init__(self, func,bind_func=None):
            self.func = func
            # self.sig = inspect.signature(func)
            if bind_func is None:
                bind_func = func

            functools.update_wrapper(self, bind_func)
        
        def __call__(self,*args,**kwargs):
            sig = inspect.signature(self.func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            # iterArg = next(iter(bound.arguments))
            # steps = bound.arguments.pop(iterArg)  # bound.args[0]
            steps = bound.args[0]
            result = []
            if sys.version_info[0] >= 3 and sys.version_info[1]>=14 and False:
                # untested
                boundFunc = functools.partial(self.func,functools.Placeholder, *bound.args[1:],**bound.kwargs) # binding the first arg sucks, fix ???
                for step in steps:
                    result.append(boundFunc(step))
            else:
                for step in steps:
                    result.append(self.func(step,*bound.args[1:], **bound.kwargs))   # SLOW 
                    # result.append(self.func(step,**bound.arguments))# almost as fast and binds args
                    #result.append(self.func(step,*args[1:], **kwargs))   # fastest
            """ attempt to coerce the type back to something nice here???, no?"""
            return result

    class parallelize_looped_method():
        """
        wrapper functor to make looped iterator methods parallel with multiprocessing
        """
        def __init__(self,func,ncPass=False,bind_func=None):
            self.func = func
            self.ncPass = ncPass
            # self.sig = inspect.signature(func)
            
            if bind_func is None:
                bind_func = func
            # self.__wrapped__ = bind_func
            functools.update_wrapper(self, bind_func)
                
            
        def __call__(self, *args, **kwargs):
            acquired_lock = False
        
            if not self.ncPass and 'nc' in kwargs:
                nc = kwargs.pop('nc')
            elif self.ncPass and 'nc' in kwargs:
                # Create pool and lock it for child functions to use
                pool = ReusablePool.get_pool(kwargs["nc"])
                ReusablePool.lock()
                acquired_lock = True
                nc = 1
            else:
                nc = 1
        
            # Bind arguments & parameters
            sig = inspect.signature(self.func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            steps = bound.args[0]
            if not is_iterable(steps): 
                steps = [steps]
            
            nc = min(nc, len(steps))
            backend = "processes"
        
            try:
                if nc > 1:
                    if type(steps) is range: 
                        stepss = list(split_range(steps, nc))
                    else:
                        stepss = np.array_split(steps, nc)
                        
                    variables = [(s,) + bound.args[1:] + tuple(bound.kwargs.values()) for s in stepss]
        
                    if backend == "processes":
                        pool = ReusablePool.get_pool(nc)
                        result = pool.starmap_async(self.func, variables)
                        result.wait()
                        result = result.get()
                        # DO NOT call ReusablePool.close() here; let finally handle it
                    else:
                        with ThreadPoolExecutor(max_workers=nc) as ex:
                            result = list(ex.map(lambda v: self.func(*v), variables))
        
                    if is_iterable(result[0]):
                        if isinstance(result[0], np.ndarray):
                            result = np.concatenate(result)
                        else:
                            result = list(itertools.chain.from_iterable(result))
                else:
                    result = self.func(steps, *bound.args[1:], **bound.kwargs)
        
                return result
        
            finally:
                # Runs on both normal return and exceptions
                if acquired_lock:
                    ReusablePool.unlock()
                ReusablePool.close()
                    
                    
    class parallelize_iterator_method():
        """
        wrapper functor to make iterator methods parallel with multiprocessing
        This is somewhat fragile because modified attributes in wrapped methods
        are not always captured by parent processes. This causes problems with 
        serializers like pickle because they often serialize by reference using __module__.
        This often results in Cant pickle errors. Dill is more robust and can 
        bypass these errors but it can still be fragile. When you add dmanage DataGroup wrapping
        and rempte protocol compputer (RPC) functionality to this multiprocessing is 
        even more touchy. That being said, the methods used here work with dmanage.strata
        and dmanage.remote.rpc with the default multiprocessing package, which uses pickle.
        Keeping this functionallity working with pickle is required by dmanage 
        guidelines because it means that the implementation is robust! That being said,
        using the multiprocess package (dill) is availiable and many time faster!
        """
        def __init__(self,func=None,ncPass=False,bind_func=None):
            if bind_func is None:
                bind_func = func
            functools.update_wrapper(self, bind_func)
            self.func = looperize(func,bind_func=bind_func)
            self.func = parallelize_looped_method(self.func,ncPass=ncPass,bind_func=bind_func)
            
        def __call__(self,*args,**kwargs):
            return self.func(*args,**kwargs)
        
    # class parallelize_iterator_method():
    #     def __init__(self,ncPass=False,bind_func=None):
    #         self.ncPass = ncPass
    #         self.bind_func = bind_func
            
    #     def __call__(self,*args,**kwargs):
    #         func = args[0]
    #         if self.bind_func is None:
    #             self.bind_func = func
    #         functools.update_wrapper(self, self.bind_func)
    #         self.func = looperize(func,bind_func=self.bind_func)
    #         self.func = parallelize_looped_method(self.func,ncPass=self.ncPass,bind_func=self.bind_func)
            
    #         # return self.func(*args,**kwargs)
    #         return self.func
        

        
elif WRAPPER_TYPE == 'funcs':
    
    ################   
    # Less picklable            
    #########################
    def looperize(func,bind_func=None):
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
        if bind_func is None:
            bind_func = func
        sig = inspect.signature(bind_func)
        @functools.wraps(bind_func)
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
    
    
    def parallelize_looped_method(func,ncPass=False,bind_func=None):
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
        
        if bind_func is None:
            bind_func = func
        sig = inspect.signature(bind_func)
        @functools.wraps(bind_func)
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

    def parallelize_iterator_method(func,ncPass=False,bind_func=None):
        """
        This is the function version of the implmentation. It is less pickleable
        
        """
        if bind_func is None:
            bind_func = func

        looped = looperize(func, bind_func=bind_func)
        parallel = parallelize_looped_method(looped,ncPass=False,bind_func=bind_func)
    
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return parallel(*args, **kwargs)
        return wrapper

if __name__ == "__main__":
    import time
    def _addOne(arg0,arg1):
        return arg0 + 1

    
    def _addOneLooped(arg0,arg1):
        if arg1:
            result = []
            for step in arg0:
                result.append(_addOne(step,arg1))
            return result
        else:
            return arg0 
        
    def addOne(arg0,arg1,nc=1):
        # addOne = looperize(_addOne)
        
        
    
        #addOne = parallelize_looped_method(_addOneLooped)
        
        # addOne = looperize(_addOne)
        # addOne = parallelize_looped_method(addOne)
        
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

    values = range(0,100000000,1)
    result = addOne(values,arg1=True,nc=1)
    # print(result)
    
    # def _mean(N,size):
    #     return np.mean(np.random.rand(size))*N

    
    # def mean(N,size,nc=1):
    #     mean = parallelize_iterator_method(_mean)
    #     startTime = time.time()
    #     nc = min(nc,N)
    #     print('Taking mean of %d arrays of size %d using %i cores...'%(N,size,nc), end=' ')
    #     result = mean(range(0,N),size,nc=nc)
    #     executionTime = (time.time()-startTime)
    #     print(' Done in %0.2f seconds'%(executionTime))
    #     return result
    
    # N = 10000
    # size = 1000000
    # result = mean(N,size,nc=4)
    
    # print(result)

    
    