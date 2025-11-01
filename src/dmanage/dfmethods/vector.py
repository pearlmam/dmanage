# -*- coding: utf-8 -*-
import pandas as pd
from dmanage.dfmethods.convert import numpy2DF,DF2Numpy
from dmanage.dfmethods import functions as func

def curl(DF):
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else:
            name = DF.columns[0]
    else:
        name = DF.name
        
    array,bounds = DF2Numpy(DF)
    s = array.shape
    keys = list(bounds.keys())
    dsteps = [bounds[key][1] - bounds[key][0] for key in keys[:len(s)-1]]
    array = func.curl(array,dsteps)
    DF = numpy2DF(array,bounds,colName='curl(%s)'%name)
    
    return DF