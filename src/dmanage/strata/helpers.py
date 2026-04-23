# -*- coding: utf-8 -*-
import inspect
import os
from dmanage.utils.sigbind import rebuild_signature

SAVE_TYPE = 'png'
SAVE_LOC = 'processed/'
def save_plot(self,fig,saveName='plot',saveLoc=None,tagVars=None,tagFormat=None,saveTag=None,saveType=None):
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
    
    
def enable_save_plot(sig):
    # modify original sig to include save parameters for helper.save_plot
    plot_sig = inspect.signature(save_plot)
    sig_required = list(plot_sig.parameters.values())[1:]
    params_existing = list(sig.parameters.values())
    sig_existing = {p.name for p in params_existing}
    new_params = [inspect.Parameter(param.name,inspect.Parameter.POSITIONAL_OR_KEYWORD,default=None if param.default is inspect._empty else param.default) 
                  for param in sig_required if param.name not in sig_existing]
    new_params = params_existing + new_params
    new_params = rebuild_signature(new_params)
    sig = sig.replace(parameters=new_params)
    return sig