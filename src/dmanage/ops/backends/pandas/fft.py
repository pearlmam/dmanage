# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

import dmanage.ops.arrays.fft
from dmanage.ops.backends.pandas.helper import cut_range
from dmanage.ops.backends.pandas.convert import numpy_to_df,df_to_numpy,replace_bounds


def fft_phase(DF):
    cols = DF.columns
    theCols = ['ang(%s)'%(col) for col in cols]
    DF = pd.DataFrame(np.angle(DF),columns=theCols,index=DF.index)
    # DF.columns = theCols
    return DF

def fft_amplitude(DF, normalize=True):
    DF = DF.abs()
    if normalize:
        DF = DF/DF.max()
    cols = DF.columns
    theCols = ['abs(%s)'%(col) for col in cols]
    DF.columns = theCols
    return DF

def fft(DF, theRange=[0.0, 1.0], axis=-1, window='hanning', ang=False, upsample=False):
    # if not issubclass(type(DF), pd.core.series.Series): 
    #     if len(DF.columns)>1:
    #         raise Exception("DF must be of type Series or of type DataFrame with one column.")
    #     else:
    #         varName = DF.columns[0]
    # else:
    #     varName = DF.name
    DF = cut_range(DF, theRange, iName=None, inplace=True)
    if not issubclass(type(DF), pd.core.series.Series): 
        cols = DF.columns
        if len(cols)>1:
            
            # iNames = DF.index.names
            # DF.columns.name = 'histNames'
            DF = DF.stack()
            DF.name = 'value'
            # DF = DF.reorder_levels(['histNames'] + iNames)
            
            if axis==-1: axis = axis-1
    else:
        cols = [DF.name]
    theCols = ['FFT(%s)'%(col) for col in cols]
 
    array,bounds = df_to_numpy(DF)
    iName = list(bounds.keys())[axis]
    x = bounds[iName]
    freq,FFT = dmanage.compute.methods.fft.fft(array, x, axis=axis, upsample=upsample, window=window)

    bounds = replace_bounds(bounds, iName, 'freq', vals=freq)
    FFT = numpy_to_df(FFT, bounds, 0)
    
    if len(cols)>1:
        FFT = FFT.unstack()[0]
        
    FFT.columns = theCols
    return FFT
    

def fft2d(DF):
    colName = DF.columns[0]
    colName = 'FFT2(%s)'%colName
    array,bounds = df_to_numpy(DF)
    dxy = []
    for value in bounds.values():
        dxy = dxy + [value[1]-value[0]]
    ft,x,y = dmanage.compute.methods.fft.fft2d(array, dxy=dxy)
    mi = pd.MultiIndex.from_product([x,y],names=['fx','fy'])
    # mi = pd.MultiIndex.from_product([y,x],names=['fy','fx'])
    DF = pd.DataFrame(ft.flatten(),index=mi,columns=[colName])
    
    
    return DF 


def windowed_fft(DF, win=None, overlap = 0.5):
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else:
            varName = DF.columns[0]
    else:
        varName = DF.name
        
    if len(DF.index.shape) > 1:
        raise Exception("DF must be 1D (only have 1 index level)")
    
    iName = DF.index.names[0]
    array,bounds = df_to_numpy(DF)
    x = bounds[iName]
    array,freq,x = dmanage.compute.methods.fft.get_windowed_fft(array, x, win=win, overlap=overlap)
    bounds = {iName:x,'freq':freq}
    DF = numpy_to_df(array, bounds, colName='amp')
    return DF



