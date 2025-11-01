# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import matplotlib as mpl


import copy

# my package methods
from dmanage.dfmethods import functions as func
from dmanage.dfmethods.convert import numpy2DF,DF2Numpy
from dmanage.dfmethods.linalg import norm


# plot1D,plot1DWPks,scatter,drawFig
    
def mi_iloc(DF,indices):
    if type(indices) is not list: indices = [indices]
    newDF = DF
    for i,index in enumerate(indices):
        ival = DF.index.get_level_values(i)[index]
        newDF = newDF.loc[ival]
    return newDF



##### might noet be needed in preference for np.array_split()?
def splitBy(DF,N,indices=[],axis=0):
    if not type(indices) is list:
        indices = [indices]
    if len(indices)==0:
        DFs = np.array_split(DF,N,axis=axis)
    else:
        if axis==1: index = DF.columns
        else: index = DF.index
        levelOrderOriginal = list(index.names)
        levelsToRemove = list(index.names)
        for indice in indices:
            levelsToRemove.remove(indice)
        levels =  indices + levelsToRemove
        
        DF = DF.reorder_levels(levels,axis=axis).sort_index(axis=axis)
        #DF = DF.reorder_levels(levels,axis=axis)
        if axis==1: index = DF.columns
        else: index = DF.index
        splitIndices = index.droplevel(levelsToRemove).unique()
        splitIndices = np.array_split(splitIndices,N)
        DFs = []
        for splitIndice in splitIndices:
            if not splitIndice.empty:
                if axis == 1:
                    DFs = DFs + [ DF.loc[:,splitIndice[0]:splitIndice[-1]] ]
                else:
                    DFs = DFs + [ DF.loc[splitIndice[0]:splitIndice[-1]] ]
    return DFs

def splitByOld(DF,index,N):
    if type(DF.index) == pd.core.indexes.multi.MultiIndex:
        index = DF.index.get_level_values(index)
    else:
        index = DF.index.values
    vals = np.array(index.unique())
    nVals = len(vals)
    splitVals = [vals[0]]
    DFs = []
    for i in range(1,N+1,1):
        splitVals = splitVals + [vals[int(round((nVals-1)*i/N))]]
        if i == N:
            DFs = DFs + [DF.iloc[index>=splitVals[i-1]]]
        else:
            
            DFs = DFs + [DF.iloc[(index>=splitVals[i-1]) & (index<splitVals[i])]]
    
    # DFs = DF
    return DFs


def cutRange(DF,theRange,iName=None,inplace=True):
    if type(DF.index) == pd.core.indexes.base.Index: iNames = [DF.index.name]
    if type(DF.index) == pd.core.indexes.multi.MultiIndex: iNames = DF.index.names
    if type(iName)==type(None): iName = iNames[-1]
    if not iName in iNames: raise Exception("'%s' is not one of the indices %s in the DataFrame"%(iName,iNames))
    
    
    # NEEDS FIXING see theRange in reduce()
    # i = DF.index.get_level_values(iName)
    # iVals = i.unique()
    # s = len(iVals)-1
    # start = iVals[int(s*theRange[0])]
    # end = iVals[int(s*theRange[1])]
    # if inplace: DF = DF.loc[(start<=i) & (i<=end)]
    # else: DF = copy.deepcopy(DF.loc[(start<=i) & (i<=end)])
    
    # will this work
    i = DF.index.get_level_values(iName)
    valRange = (i.max()-i.min())*np.array(theRange)+i.min()
    iRange = (i >= valRange[0]) & (i <= valRange[1])
    DF = DF.iloc[iRange].sort_index()
    
    return DF
    
def reduce(DF,iName=None,method='mean',iApply=False,inplace=False,block=False,**kwargs):
    if type(method) is dict:
        DFs=[]
        for methodKey,cols in method.items():
            DFs = DFs + [_reduce(DF.loc[:,cols],iName,methodKey,iApply,inplace,block,**kwargs)]
        DF = pd.concat(DFs,axis=1)
    else:
        DF = _reduce(DF,iName,method,iApply,inplace,block,**kwargs)
    return DF

def _reduce(DF,iName=None,method='mean',iApply=False,inplace=False,block=False,**kwargs):
    """
    reduce the dimension of the Dataframe using the method input. the input DF may have multiple columns
    """
    
    aggMethods = ['mean','sum','min','max','first','count','last','std','var']
    availMethods = aggMethods + ['norm','value']
    #iMethods = ['i'+method for method in availMethods] # get the index of the method, ie: location of the mean rather than the mean itself
    iMethods = ['imax','imin']
    allMethods = availMethods + iMethods
    if issubclass(type(DF),pd.core.series.Series): 
        cols = [DF.name]
        DF = DF.to_frame()
    elif issubclass(type(DF),pd.core.frame.DataFrame): 
        cols = DF.columns
    else: 
        raise Exception('DF must be either a pandas DataFrame or pandas Series')
    if (type(DF.index) == pd.core.indexes.base.Index): #  or (type(DF.index) == pd.core.indexes.numeric.Float64Index): pd.core.indexes.range.RangeIndex???
        iNames = [DF.index.name]
    if type(DF.index) == pd.core.indexes.multi.MultiIndex: 
        iNames = list(DF.index.names)
    if type(iName)==type(None): 
        iName = iNames[-1]
    if iName in iNames: iNames.remove(iName)
    else: 
        if block: raise Exception("'%s' is not one of the indices %s in the DataFrame"%(iName,iNames))
        else: 
            print("'%s' is not one of the indices %s in the DataFrame, no reduction implemented"%(iName,iNames))
            return DF
    if not inplace: DF = copy.deepcopy(DF)
    if iApply:
        DF[iName]=list(DF.index.get_level_values(iName))
        cols = DF.columns
    
    if 'theRange' in kwargs:
        
        
        theRange = kwargs['theRange'] 
        i = DF.index.get_level_values(iName)
        valRange = (i.max()-i.min())*np.array(theRange)+i.min()
        iRange = (i >= valRange[0]) & (i <= valRange[1])
        DF = DF.iloc[iRange]
        # iVals = i.unique()
        # s = len(iVals)-1
        # start = iVals[int(s*theRange[0])]
        # end = iVals[int(s*theRange[1])]
        # DF = DF.loc[(start<=i) & (i<=end)]
    
    if method in aggMethods:
        if len(DF.index.names) == 1: DF = eval('DF.'+method+'()')
        else: DF = eval('DF.groupby(iNames).'+method+'()')
    
    elif method == 'norm':
        if 'order' in kwargs: order = kwargs['order'] 
        else: order = 2
        DF = norm(DF,iName,order)
        
    elif method == 'value':
        iNames.insert(0,iName)  # reorder the iNames so it's easy to take a slice
        if 'value' in kwargs: value = kwargs['value'] 
        else: raise Exception("With method='value', an additional arge 'value' must be specified")
        value = getClosestValue(DF,iName,value)
        DF = DF.reorder_levels(iNames).loc[value]
    
    elif method == 'wmean':
        if 'wcol' in kwargs: wcol = kwargs['wcol'] 
        else: wcol = 'weight'
        if not wcol in cols: raise Exception("DataFrame needs a kwarg wcol defined or a 'weight' column to calculate the weighted mean")
        if any(DF[wcol]<0): 
            print("Warning: Weighted mean can not have negative values in '%s'"%wcol)
        else:
            # weighted mean, requires weight col
            if len(DF.index.names) == 1: wSum = DF[wcol].sum()
            else: wSum = DF.groupby(iNames)[wcol].transform('sum') # grouped weighted sum
            resultCols = list(cols)
            resultCols.remove(wcol)
            
            # chained assignment here sometimes, how to remove
            # DF[resultCols] = DF[resultCols].multiply(DF[wcol],axis='index')
            # DF[resultCols] = DF[resultCols].divide(wSum,axis='index')
            
            DF.loc[:,resultCols] = DF[resultCols].multiply(DF[wcol],axis='index')
            DF.loc[:,resultCols] = DF[resultCols].divide(wSum,axis='index')
            if len(DF.index.names) != 1: DF = DF.groupby(iNames).sum()
            else: DF = DF.sum()
        
        
    elif method in iMethods:
        if 'refCol' in kwargs: refCol = kwargs['refCol'] 
        elif len(cols)==1: refCol = cols[0]
        else: raise Exception("With a multiple column DataFrame, the reference column 'refCol' must be specified for index methods")
        if len(DF.index.names) == 1:
            I = eval('DF[refCol].idx%s()'%method[1:])
            i = pd.Index([I],name=DF.index.names[0])
            DF = DF.loc[i].reset_index().iloc[0]
        else:
            mi = eval('DF[refCol].groupby(iNames).idx%s()'%method[1:])
            DF = DF.loc[mi].reset_index(iName)
        
        
      
    # elif method[0] == 'i':   #### OBSOLETE
    #     if 'refCol' in kwargs: refCol = kwargs['refCol'] 
    #     elif len(cols)==1: refCol = cols[0]
    #     else: raise Exception("With a multiple column DataFrame, the reference column 'refCol' must be specified for index methods")
    #     if len(DF.index.names) == 1:
    #         I = DF[refCol].subtract(reduce(DF,iName,method=method[1:])[refCol]).abs().idxmin(axis=1)
    #         i = pd.Index([I],name=DF.index.names[0])
    #         DF = DF.loc[i].reset_index().iloc[0]
    #     else:   
    #         I = DF[refCol].unstack().subtract(reduce(DF,iName,method=method[1:])[refCol],axis=0).abs().idxmin(axis=1)
    #         mi = pd.MultiIndex.from_arrays([I.index,I],names=(DF.index.names))
    #         DF = DF.loc[mi].reset_index(level=iName)
    #     # below is all in one line but wont work for multi column DataFrames... And might need a reindex.
    #     #DF1['Evane0'].unstack().subtract(DD.DFM.reduce(DF1,'point',method='mean')['Evane0'],axis=0).abs().idxmin(axis=1)
        
    else: raise Exception("Method: '%s' is not a known method. Choose from: %s"% (method,allMethods))
    
    return DF

def weightedConcat(DFlist,col='weight',nc=1):
    if len(DFlist)==1:
        DF = DFlist[0]
    elif len(DFlist)>1:
        if nc>1:
            DF = None
        else:
            DF = _weightedConcat(DFlist,col)
    else:
        DF = None
    return DF
        
def _weightedConcat(DFlist,col='weight'):
    """
    requires column named 'weight'
    """
    DF = pd.concat(DFlist)
    iNames = list(DF.index.names)
    wSum = DF.groupby(iNames)[col].transform('sum') # grouped weighted sum
    wCols = list(DF.columns)
    wCols.remove(col)
    DF[wCols] = DF[wCols].multiply(DF[col],axis='index')
    DF[wCols] = DF[wCols].div(wSum,axis='index')
    DF = DF.groupby(iNames).sum() 
    return DF

def getClosestValue(DF,iName,value):
    iLevel = [i for i in range(len(DF.index.names)) if DF.index.names[i] == iName][0]
    values = DF.index.get_level_values(iLevel).unique().to_numpy()
    if not value in values:
        valueIndex = np.argmin( np.abs(values-value) )
        value = values[valueIndex]
    return value

def getSlice(DF,iName,value,drop=True):
    """
    

    Parameters
    ----------
    DF :DataFrame
        DESCRIPTION.
    iName : string
        DESCRIPTION.
    value : anything
        DESCRIPTION.

    Returns
    -------
    DF : DataFrame
        The DataFrame will only contain the rows where the index with iName has the value

    """
    iLevel = [i for i in range(len(DF.index.names)) if DF.index.names[i] == iName][0]
    value = getClosestValue(DF,iName,value)
    indices = DF.index.get_level_values(iLevel)==value    
    DF = DF.iloc[indices]
    if drop: DF = DF.reset_index(iName,drop=True)
    
    return DF

def windowedInfo(DF,win=None,overlap=0.5,info='period',window='hanning',**kwargs):
    array,bounds = DF2Numpy(DF)
    iName = list(bounds.keys())[len(array.shape)-1]
    x = bounds[iName]
    Is,xs = func.getWindowedInfo(array,x,win=win,overlap=overlap,info=info,window=window)
    return Is,xs


def getStableWidth(DF,iSweep,checkCols=[],stableCol='stable'):
    iNames = []

    if iSweep in DF.index.names:
        DF = DF.reset_index(iSweep)
        iNames = iNames + [iSweep]
    elif iSweep in DF.columns:
        pass
    
    for checkCol in checkCols:
        if checkCol in DF.columns:
            pass
        elif checkCol in DF.index.names:
            DF = DF.reset_index(checkCol)
            iNames = iNames + [checkCol]
        else:
            print('%s is niether an index or a column, ignoring...'%checkCol)
        
        grp = DF[checkCol].loc[DF[stableCol]].groupby(DF.index.names)
        stabWidth = grp.max() - grp.min()
        DF['stabW(%s,%s)'%(iSweep,checkCol)]=stabWidth
        DF = DF.set_index(iNames)
    return DF

def getStableData(DF,method,iSweep,checkCols=[],stableCol='stable'):
    # iNames = list(DF.index.names)
    iNames = []
    if iSweep in DF.index.names:
        DF = DF.reset_index(iSweep)
        iNames = iNames + [iSweep]
    elif iSweep in DF.columns:
        pass
    
    for checkCol in checkCols:
        if checkCol in DF.columns:
            pass
        elif checkCol in DF.index.names:
            DF = DF.reset_index(checkCol)
            iNames = iNames + [checkCol]
        else:
            print('%s is niether an index or a column, ignoring...'%checkCol)

        grp = DF[checkCol].loc[DF[stableCol]].groupby(DF.index.names)
        if method == 'width':
            stabData = grp.max() - grp.min()
            colName = 'stabW(%s,%s)'%(iSweep,checkCol)
        elif method == 'max':
            stabData = grp.max()
            colName = 'stabMax(%s,%s)'%(iSweep,checkCol)
        elif method == 'max':
            stabData = grp.min()
            colName = 'stabMin(%s,%s)'%(iSweep,checkCol)
        DF[colName]=stabData
        DF = DF.set_index(iNames,append=True)
    return DF

def binDF(DF,binVars,bins,inplace=False):
    """
    This bins the DataFrame by the column labeled <var> by the <bins> and the agregation in methods
    bins can be an integer representing the number of bins, or a list of the bin breaks

    Parameters
    ----------
    DF : pandas.DataFrame
        DataFrame that has columns to bin...
    binVars : str, list
        names of the columns to bin
    bins : int, list
        The number of bins for each binVar
    inplace : bool, optional
        To bin in place or not. The default is False.

    Raises
    ------
    Exception
        if the len(bins) is not equal to len(binVars)

    Returns
    -------
    DF : pandas.DataFrame
        bined DataFrame

    """
    
    if type(binVars) is not list:
        binVars=[binVars]
    if type(bins) is not list:
        bins = [bins]*len(binVars)
        
    if len(binVars) != len(bins): raise Exception('length of binVars must be equal to the length of bins')
    if not inplace: DF = copy.deepcopy(DF)
    
    for i,binVar in enumerate(binVars):
        DF[binVar] = pd.cut(DF[binVar],bins[i])
        # DF[binVar] = pd.IntervalIndex(pd.cut(DF[binVar],bins[i])) # doesnt work well with grouping and keep uniform array... I think.
    
        
    # NaN entries for rBins, and phiBins are electrons that cant be binned? 
    # they must be removed
    # if any other columns have a NaN, they too will be removed, which could be bad.
    return DF



def genBinBreaks(DF,binCols,bins,phiRange='2pi'):
    """generate bin breaks using the min and max"""
    if type(binCols) is not list: binCols = [binCols]
    if type(bins) is not list: bins = [bins]*len(binCols)
    if len(binCols) != len(bins): raise Exception("length of bins must be equal to the length of binCols")
    
    binBreaks = [0]*len(binCols)
    for i,binVarName in enumerate(binCols):
        minmax = DF[binCols[i]].agg(['min','max'])
        binBreaks[i] = list(np.linspace(minmax[0],minmax[1],bins[i]+1))
        binBreaks[i] = [*set(binBreaks[i])]
        binBreaks[i].sort()
        if len(binBreaks[i]) == 1:
            binBreaks[i] = []
    try: 
        iPhi = binCols.index('phi')
        np.array(binBreaks[iPhi])
        if phiRange == 'pi':
            binBreaks[iPhi] = list((np.array(binBreaks[iPhi])+np.pi)%(2*np.pi) - np.pi)
        elif phiRange == '2pi':
            binBreaks[iPhi] = list(np.array(binBreaks[iPhi])%(2*np.pi))
        binBreaks[iPhi].sort()
    except: 
        pass
    
    return binBreaks


  

