# -*- coding: utf-8 -*-
import inspect
import os
from dmanage.utils.sigbind import rebuild_signature,check_variadic,overwrite_defaults

SAVE_TYPE = 'png'
SAVE_LOC = 'processed/'
def savePlot(self,fig,saveName='plot',saveLoc=None,tagVars=None,tagFormat=None,saveTag=None,saveType=None):
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
    
    
def enable_savePlot(sig,func,instance):
    """
    TO DO: add check to see if all func parameters explicitly define savePlot parameters
    Right now it requires *args and **kwargs
    """
   
    sig = inspect.signature(func)
    plot_sig = inspect.signature(savePlot)
    if not check_variadic(sig):
        raise TypeError("Method '%s' requires variadic parameters (*args,**kwargs) to use 'savePlot' override. "%func.__name__)

    # modify original sig to include save parameters for helper.save_plot
    sig_required = list(plot_sig.parameters.values())[1:]
    params_existing = list(sig.parameters.values())
    sig_existing = {p.name for p in params_existing}
    
    
    new_params = [inspect.Parameter(param.name,inspect.Parameter.POSITIONAL_OR_KEYWORD,default=None if param.default is inspect._empty else param.default) 
                  for param in sig_required if param.name not in sig_existing]
    new_params = params_existing + new_params
    new_params = rebuild_signature(new_params)
    sig = sig.replace(parameters=new_params)
    sig = overwrite_defaults(sig,saveLoc=instance.resDir) # use saveLoc from instance
    return sig

def enable_override(func,instance):
    sig = inspect.signature(func)
    if func._override == 'savePlot':
        sig = enable_savePlot(sig,func,instance)
    return sig


    
