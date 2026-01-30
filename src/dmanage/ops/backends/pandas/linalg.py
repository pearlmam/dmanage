# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

def norm(DF,iName,order=2):
    """
    takes the norm of the DF with respect to the iName index. The input DF may have multiple columns at the moment

    Parameters
    ----------
    DF : pandas DataFrame
    iName : string
        name of the index to take the norm over
    order : float
        norm order, see np.linalg.norm

    Returns
    -------
    DF : pandas DataFrame
        The DF will have one less index level

    """
    if issubclass(type(DF),pd.core.series.Series): 
        cols = [DF.name]
        DF = DF.to_frame()
    elif issubclass(type(DF),pd.core.frame.DataFrame): 
        cols = DF.columns
        
    if len(DF.index.names) == 1: 
        scaler = np.linalg.norm(DF.to_numpy()[:,0],ord=order,axis=0)
        DF = pd.DataFrame([scaler],cols)[0]
    else:
        if len(cols)>1: DF = DF.stack()
        DF = DF.unstack(level=iName)
        mi = DF.index
        array = np.linalg.norm(DF.to_numpy(),ord=order,axis=1)
        if len(cols)>1: DF = pd.DataFrame(array,mi).unstack(level=-1)[0]
        else: DF = pd.DataFrame(array,mi,cols)
    return DF