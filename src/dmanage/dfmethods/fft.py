# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

from dmanage.dfmethods.process import cutRange
from dmanage.dfmethods.convert import numpy2DF,DF2Numpy,replaceBounds
from dmanage.dfmethods import functions as func

def FFTphase(DF):
    cols = DF.columns
    theCols = ['ang(%s)'%(col) for col in cols]
    DF = pd.DataFrame(np.angle(DF),columns=theCols,index=DF.index)
    # DF.columns = theCols
    return DF

def FFTamplitude(DF,normalize=True):
    DF = DF.abs()
    if normalize:
        DF = DF/DF.max()
    cols = DF.columns
    theCols = ['abs(%s)'%(col) for col in cols]
    DF.columns = theCols
    return DF

def FFT(DF,theRange=[0.0,1.0],axis=-1,window='hanning',ang=False,upsample=False):
    # if not issubclass(type(DF), pd.core.series.Series): 
    #     if len(DF.columns)>1:
    #         raise Exception("DF must be of type Series or of type DataFrame with one column.")
    #     else:
    #         varName = DF.columns[0]
    # else:
    #     varName = DF.name
    DF = cutRange(DF,theRange,iName=None,inplace=True)    
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
 
    array,bounds = DF2Numpy(DF)
    iName = list(bounds.keys())[axis]
    x = bounds[iName]
    freq,FFT = func.FFT(array,x,axis=axis,upsample=upsample,window=window)

    bounds = replaceBounds(bounds,iName,'freq',vals=freq)
    FFT = numpy2DF(FFT,bounds,0)
    
    if len(cols)>1:
        FFT = FFT.unstack()[0]
        
    FFT.columns = theCols
    return FFT
    

def FFT2D(DF):
    colName = DF.columns[0]
    colName = 'FFT2(%s)'%colName
    array,bounds = DF2Numpy(DF)
    dxy = []
    for value in bounds.values():
        dxy = dxy + [value[1]-value[0]]
    ft,x,y = func.FFT2D(array,dxy=dxy)
    mi = pd.MultiIndex.from_product([x,y],names=['fx','fy'])
    # mi = pd.MultiIndex.from_product([y,x],names=['fy','fx'])
    DF = pd.DataFrame(ft.flatten(),index=mi,columns=[colName])
    
    
    return DF 


def windowedFFT(DF,win=None,overlap = 0.5):
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
    array,bounds = DF2Numpy(DF)
    x = bounds[iName]
    array,freq,x = func.getWindowedFFT(array,x,win=win,overlap=overlap)
    bounds = {iName:x,'freq':freq}
    DF = numpy2DF(array,bounds,colName='amp')
    return DF



