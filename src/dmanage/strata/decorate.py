# -*- coding: utf-8 -*-
import os
import functools

__all__ = ["override","plot_override"]

def override(kind='default',level=None,ncPass=False,**kwargs):
    """
    

    Parameters
    ----------
    kind : string, optional
        This is the value of the _override attribute. This chooses which kind of 
        override to apply. The default is 'default'.
    level : int, optional
        NOT IMPLEMENTED. This will choose which level to apply the override.
        The default is None.

    Returns
    -------
    function
        This is the same function to be decorated but with an added _override attribute
        with kind as the value.

    """
    
    def _override(func):
        """Decorator to add an override attribute for a method."""
        setattr(func, '_override', kind)
        setattr(func, '_level',level)
        setattr(func, '_ncPass',ncPass)
        setattr(func, '_kwargs',kwargs)
        return func
    
    # # detects if decorator was used with or without parentheses, add _func arg in first position
    # # Case 1: used as @override
    # if _func is not None and callable(_func):
    #     return  _override(_func)
    
    # Case 2: used as @override(...)
    return _override
    


class plot_override():
    """decorate for plot saving
    doesnt work well with data groups....
    self._func naming is important because when the group make_wrapper functools
    updates the wrapper, it overwrites shared wrapper attributes. 
    
    This also makes the wrapped function appear like this class, which is not an instance to make_wrapper
    the inspected signature contains a self parameter which is removed in helpers.enable_override
    
    Right now this still can't be pickled 
    Error with pickle
    PicklingError: Can't pickle <function MyDataUnit.plot3 at 0x7a837deb09a0>: it's not the same object as testObjects.MyDataUnit.plot3
    
    error with dill, it appears like it needs to pickle the entire datagroup...
    RuntimeError: Datagroup should not be pickled. Parallelism should only pickle DataUnit
    
    I also need to fix the signature stuff in helpers, the inputs are in the wrong order
    
    """
    def __init__(self,func):
        setattr(func, '_override', 'plot2')
        self._func = func    # self._func used so that it doesnt conflict with make_wrapper.func!!!
        functools.update_wrapper(self, func)
    # def __get__(self, instance, owner):
    #     # This works with unit alone, fails with group
    #     if instance is None:
    #         return self
    #     return functools.partial(self.__call__, instance)
    
    def __get__(self, instance, owner):
        # store instance and return self as callable

        self.instance = instance
        return self
    
    
    def __call__(self,saveName='plot',saveLoc=None,tagVars=[],tagFormat=None,*args,**kwargs):
        if getattr(self.instance,'saveType', False):
            saveType = self.instance.saveType
        else:
            saveType = 'png'
        if saveLoc is None:
            saveLoc = self.instance.resDir
        os.makedirs(saveLoc,exist_ok=True)
        
        fig, ax = self._func(self.instance, *args, **kwargs)
        saveTag = self.instance.gen_tag(tagVars,tagFormat)
        fig.savefig('%s%s_%s.%s'%(saveLoc,saveName,saveTag,saveType) , bbox_inches='tight', format=saveType)
        return fig,ax

if __name__ == "__main__":
    # @add_attribute('_override',True)
    # def test():
    #     pass

    @override('hi',a=1,b=2)
    def test():
        pass


    print(test)
    print(test._override)
    print(test._level)
    print(test._args)
    
    pass