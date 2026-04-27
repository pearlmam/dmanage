# -*- coding: utf-8 -*-
import inspect
import os
from dmanage.utils.sigbind import rebuild_signature,check_variadic,overwrite_defaults

SAVE_TYPE = 'png'
SAVE_LOC = 'processed/'

class PurePython:
    """Inheritance class to make DataUnit a pure python class, for __bases__ assignment in makeDataUnit()"""
    def __init__(self,dataPath,*args,**kwargs):
        pass
    
def _savePlot(self,fig,saveName='plot',saveLoc=None,tagVars=None,tagFormat=None,saveTag=None,saveType=None):
    """
    this function is behind a layer so that kwargs can be overwritten from the data group wrapper
    The data group wrapper signature binds and applies defaults for robustness
    This makes it difficult to overwrite those defaults in the calling function.
    """
    if saveType is None:
        if hasattr(self,'saveType'):
            saveType = self.saveType
        else:
            saveType = SAVE_TYPE
    if saveLoc is None:
        if hasattr(self,'resDir'):
            saveLoc = self.resDir
        else:
            saveLoc = './' + SAVE_LOC
    os.makedirs(saveLoc,exist_ok=True)
    
    if tagVars is not None and hasattr(self,'gen_tag'):
        saveTag = self.gen_tag(tagVars=tagVars,format=tagFormat)
    if saveTag is None:
        saveTag = ''
    else:
        saveTag = '_' + saveTag

    fig.savefig('%s%s%s.%s'%(saveLoc,saveName,saveTag,saveType) , bbox_inches='tight', format=saveType)
    
def savePlot(self,fig,args,kwargs,*_args,**_kwargs):
    sig = inspect.signature(_savePlot)
    bound = sig.bind(self, fig, *args, **kwargs)
    bound.apply_defaults()
    bound.arguments.update(_kwargs)
    return _savePlot(**bound.arguments)
    
    
def enable_savePlot(sig,func,instance):
    """
    synchronize calling function and savePlot signatures
    It also uses the data group  instance to set the default write directory
    
    
    """
    sig = sync_sigs(func,_savePlot)
    sig = overwrite_defaults(sig,saveLoc=getattr(instance,'resDir',None)) # use saveLoc from instance
    return sig

def sync_sigs(callFunc,subFunc):
    """This takes the calling function and updates the signature to include subfunc parameters
    
    TO DO: 
        add check to see if all func parameters explicitly define savePlot parameters?
        Right now it requires ``*args`` and ``**kwargs``
    """
    sig = inspect.signature(callFunc)
    plot_sig = inspect.signature(subFunc)
    if not check_variadic(sig):
        raise TypeError("Method '%s' requires variadic parameters (*args,**kwargs) to use 'savePlot' override. "%callFunc.__name__)

    # modify original sig to include save parameters for helper.save_plot
    sig_required = list(plot_sig.parameters.values())[1:]
    params_existing = list(sig.parameters.values())
    sig_existing = {p.name for p in params_existing}
    
    
    new_params = [inspect.Parameter(param.name,inspect.Parameter.POSITIONAL_OR_KEYWORD,default=None if param.default is inspect._empty else param.default) 
                  for param in sig_required if param.name not in sig_existing]
    new_params = params_existing + new_params
    new_params = rebuild_signature(new_params)
    sig = sig.replace(parameters=new_params)
    return sig


def enable_override(func,instance):
    """
    The group method wrapper calls this for all overridden methods 
    This makes sure the func signature is solid
    """
    sig = inspect.signature(func)
    if func._override == 'savePlot':
        sig = enable_savePlot(sig,func,instance)
    elif func._override == 'plot2':
        params = list(sig.parameters.values())
        new_params = params[1:]  # Drops 'self'
        sig = sig.replace(parameters=new_params)
        # sig = sync_sigs(func,decorate.plot_override???)
        
    return sig


    
