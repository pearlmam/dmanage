# -*- coding: utf-8 -*-
import pandas as pd

import dmanage.ops.arrays.vector
from dmanage.ops.backends.pandas.convert import numpy_to_df,df_to_numpy


def curl(DF):
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else:
            name = DF.columns[0]
    else:
        name = DF.name
        
    array,bounds = df_to_numpy(DF)
    s = array.shape
    keys = list(bounds.keys())
    dsteps = [bounds[key][1] - bounds[key][0] for key in keys[:len(s)-1]]
    array = dmanage.compute.methods.vector.curl(array, dsteps)
    DF = numpy_to_df(array, bounds, colName='curl(%s)' % name)
    
    return DF