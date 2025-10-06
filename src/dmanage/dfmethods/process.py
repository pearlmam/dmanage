# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import matplotlib as mpl
if mpl.cbook._get_running_interactive_framework() == 'headless':
    mpl.use('agg')
    mpl.rcParams['path.simplify'] = True

import copy
from scipy import signal
from scipy.optimize import curve_fit

from dmanage.dfmethods import functions as func
from dmanage.dfmethods.convert import numpy2DF,DF2Numpy,replaceBounds
from dmanage.dfmethods.plot import plot1D,plot1DWPks,scatter,drawFig
    
def mi_iloc(DF,indices):
    if type(indices) is not list: indices = [indices]
    newDF = DF
    for i,index in enumerate(indices):
        ival = DF.index.get_level_values(i)[index]
        newDF = newDF.loc[ival]
    return newDF

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

def weightedConcat(DFlist,nc=1):
    if len(DFlist)==1:
        DF = DFlist[0]
    elif len(DFlist)>1:
        if nc>1:
            DF = None
        else:
            DF = _weightedConcat(DFlist)
    else:
        DF = None
    return DF
        
def _weightedConcat(DFlist):
    """
    requires column named 'weight'
    """
    DF = pd.concat(DFlist)
    iNames = list(DF.index.names)
    wSum = DF.groupby(iNames)['weight'].transform('sum') # grouped weighted sum
    wCols = list(DF.columns)
    wCols.remove('weight')
    DF[wCols] = DF[wCols].multiply(DF['weight'],axis='index')
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

def findPks(DF,maxPks=20,hRatio=None,pRatio=None,tRatio=None,height=None,**kwargs):
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else:
            varName = DF.columns[0]
    else:
        varName = DF.name
    if len(DF.index.shape) > 1:
        raise Exception("DF must be 1D (only have 1 index level)")
    
    y,bounds = DF2Numpy(DF)
    iName = list(bounds.keys())[len(y.shape)-1]
    x = bounds[iName]
    
    xpks,ypks,props = func.findPeaks(x,y,hRatio=hRatio,pRatio=pRatio,tRatio=tRatio,height=height,**kwargs)
    
    # shorten peak list to < maxPks
    if len(ypks)>maxPks:
        ypks = ypks[0:maxPks] # remove simulation time frequency
        xpks = xpks[0:maxPks] # remove simulation time frequency
        
    numbers = [str(i) for i in range(len(xpks))]
    numbers = np.array(numbers)
    out = np.stack([xpks,ypks])
    i = pd.Index(xpks,name = iName)
    peaksDF = pd.DataFrame(ypks, columns=[varName],index=i)
    return peaksDF,props
    
    # peaksDF = pd.DataFrame(out, columns=['Freq\n[GHz]','Amp\n[arb]'])
    
    #output = peaksDF.to_string(formatters={'Freq [GHz]':'{:,.2f}'.format,'Per [ns]':'{:,.2f}'.format, 'Amp':'{:,.2f}'.format})
    #output = tabulate(peaksDF,floatfmt=".2f",headers="keys",tablefmt="plain",numalign="left")

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

def windowedInfo(DF,win=None,overlap=0.5,info='period',window='hanning',**kwargs):
    array,bounds = DF2Numpy(DF)
    iName = list(bounds.keys())[len(array.shape)-1]
    x = bounds[iName]
    Is,xs = func.getWindowedInfo(array,x,win=win,overlap=overlap,info=info,window=window)
    return Is,xs


def windowedPeriod(DF,win=None,overlap=0.5,window='hanning',inverse=False):
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else:
            name = DF.columns[0]
    else:
        name = DF.name
        
    if type(DF.index) == pd.core.indexes.multi.MultiIndex:
        iNames = DF.index.names
        if len(iNames)>1: raise Exception('Index must have only one level')
        
    array,bounds = DF2Numpy(DF)
    iName = list(bounds.keys())[len(array.shape)-1]
    x = bounds[iName]
    Ts,xs = func.getWindowedPeriod(array,x,win=win,overlap = overlap,window=window)
    
    if inverse: 
        if type(Ts) !=type(None): Ts=1/Ts
        col = 'freq(%s)'%name
    else:
        col = 'per(%s)'%name
    DF = pd.DataFrame(Ts,index=xs,columns=[col])
    DF.index.name = iName
    return DF

def getPhase(DF,refSignal='cos',period=None,hRatio=0.4,pRatio=0.3,phiRange='2pi',debug=False,fignum=1):
    
    if not issubclass(type(DF), pd.core.frame.DataFrame): 
        DF = DF.to_frame()

    if type(DF.columns) is pd.core.indexes.multi.MultiIndex:
        theIndexName = DF.columns.names[-1]
    elif not type(DF.columns.name) is type(None):
        theIndexName = DF.columns.name
    else:
        theIndexName = 'diagnostic'
    phi = []
    cols = []
    for col in DF.columns:        
        array,bounds = DF2Numpy(DF[col])
        iName = list(bounds.keys())[len(array.shape)-1]
        x = bounds[iName]
        phi = phi + [func.getPhase(array,x=x,refSignal=refSignal,period=period,hRatio=hRatio,pRatio=pRatio,debug=debug,fignum=fignum)]
        if type(col) is tuple:
            theCol = col[-1]
        else:
            theCol = col
        # theCol = col
        cols = cols + [theCol]
    # if len(DF.columns)==1:
    #     phi = phi[0]
    #     cols = cols[0]
    DF1 = pd.DataFrame(data = phi, index=cols)
    DF1.columns = ['phase']
    DF1.index.name = theIndexName
    # if len(DF1) == 1:
    #     DF1 = DF1.reset_index(drop=True)
    
    if phiRange == '2pi':
        DF1 = ((DF1+2*np.pi)%(2*np.pi))
    elif phiRange == '2pi/pi':
        DF1 = ((DF1+2*np.pi)%(2*np.pi))/np.pi
    elif phiRange == 'pi':
        DF1 = (DF1+np.pi)%(2*np.pi) - np.pi
    
    
    return DF1

def getPeriod(DF,hRatio=0.5,pRatio=0.5,window='hanning',periodicPad=False,strictCheck=False,debug=False):
    """
    get the period of a signal y

    Parameters
    ----------
   
    """
    if not issubclass(type(DF), pd.core.frame.DataFrame): 
        DF = DF.to_frame()
    DF = DF.dropna()
    T = []
    for col in DF.columns:
        array,bounds = DF2Numpy(DF[col])
        iName = list(bounds.keys())[len(array.shape)-1]
        x = bounds[iName]
        T = T + [func.getPeriod(array,x=x,hRatio=hRatio,pRatio=pRatio,window=window,periodicPad=periodicPad,strictCheck=strictCheck,debug=debug)]
    if len(DF.columns)==1:
        T = T[0]    
    # DF = pd.DataFrame(T)
    return T

def getSkewAsymmetry(DF):
    DF = DF.dropna()
    DF = DF - DF.mean()

    denom = (DF**2).mean()**(3/2.)
    # skew = (data**3).mean()/data.std()**3
    skew = (DF**3).mean()/denom
    skew.name='skew'
    asym = (np.imag(signal.hilbert(DF,axis=0))**3).mean(axis=0)/denom
    asym.name = 'asym'
    return pd.concat([skew,asym],axis=1)
        
def getSignalInfo(DF):
    info = getSkewAsymmetry(DF)
    DF = DF.dropna()
    DF = DF - DF.mean()
    info['rms'] = np.sqrt((DF**2).mean(axis=0))
    info['pp'] = DF.max()-DF.min()
    return info

def checkStability(DF,method='fft',debug=False,**kwargs):
    
    if 'fignum' in kwargs.keys():
            fignum = kwargs['fignum']
    else:
        fignum = 10
    

    if method == 'fft':
        """
        requires: noiseLevel, the noise level of signal in dB 20*log10(DF)
        optional: cutoff=[0,inf], cutoff frequencies to ignore
                 
                  
        """
        noiseLevel=None
        if 'noiseLevel' in kwargs.keys():
            noiseLevel = kwargs['noiseLevel']
        else:
            raise Exception("kwarg 'noiseLevel' is required for checkStability'")
        
        if 'cutoff' in kwargs.keys():
            cutoff = kwargs['cutoff']
            fHigh = cutoff[1]
            fLow = cutoff[0]
        else:
            fHigh=1e100
            fLow=0    
        DF = FFT(DF,window='hanning')
        DF = FFTamplitude(DF)
        DF = 20*np.log10(DF)
        DF = DF.iloc[ (DF.index.get_level_values(0)>=fLow) & (DF.index.get_level_values(0)<=fHigh) ]
        DFpks,props = findPks(DF,maxPks=10,hRatio=None,pRatio=0.05,height=noiseLevel)
        if debug:
            fig,ax = plot1DWPks(DF, fig=fignum,pRatio=0.05,height=noiseLevel)
        Npks = len(DFpks)
        NpksCheck = 1
        if Npks == NpksCheck:
            stableFFT = True
        else:
            stableFFT = False
        stable = stableFFT
    
    if method == 'powerRing':
        """
        requires: cutoff, a list of the cutoff frequencies
        optional: filt=bandpass, the filter type
                  hRatio=None, height ratio of peak finder
                  pRatio=None, prominance of peak finder
                  
        """
        #### required
        if 'cutoff' in kwargs.keys():
            cutoff = kwargs['cutoff']
        else:
            raise Exception("kwarg 'cutoff' is required for checkStability of method '%s'"%(method))
        
        ##### Optional
        if 'filt' in kwargs.keys():
            filt = kwargs['filt']
        else:
            filt='bandpass'
        if 'hRatio' in kwargs.keys():
            hRatio = kwargs['hRatio']
        else:
            hRatio=None
        if 'pRatio' in kwargs.keys():
            pRatio = kwargs['pRatio']
        else:
            pRatio=None
        
        ###### filter check: check for oscillations
        NpksCheck = 0
        if filt.lower() == 'highlow':
            flow = min(cutoff)
            fhigh = max(cutoff)
            DFfilt = applyFilter(DF,method='high',cutoff=flow,order=3,axis=-1)
            if debug: 
                fig,ax = plot1D(DFfilt,fig=fignum)
                fignum = fignum + 1
            DFfilt = applyFilter(DFfilt,method='low',cutoff=fhigh,order=3,axis=-1)
        elif filt.lower() == 'bandpass':
            flow = min(cutoff)
            fhigh = max(cutoff)
            DFfilt = applyFilter(DF,method='band',cutoff=cutoff,order=3,axis=-1)
            NpksCheck = 1
        elif filt.lower() == 'lowdiff':
            fhigh = max(cutoff)
            DFfilt = applyFilter(DF,method='low',cutoff=fhigh,order=3,axis=-1)
            if debug: 
                fig,ax = plot1D(DFfilt,fig=fignum)
                fignum = fignum + 1
            DFfilt = DFfilt.diff()
        elif method.lower() == 'abs':
            DFfilt = DF.abs()
            
        else:
            DFfilt = copy.deepcopy(DF)

        DFpks,props = findPks(DFfilt,maxPks=10,hRatio=hRatio,pRatio=pRatio)
        
        Npks = len(DFpks)
        stable = False
        if Npks == NpksCheck:
            stableFilt = True
        else:
            stableFilt = False
                
        if debug: 
            fig,ax = plot1D(DFfilt,fig=fignum)
            fig,ax = scatter(DFpks,fig=fig,clear=False,color='b')
            ax.relim()
            ax.autoscale()
            ax.set(title='Peak Check: detect=%0.0f, max=%0.0f, stable = %0.0f'%(Npks,NpksCheck,stableFilt))
            fig = drawFig(fig)
            fignum = fignum + 1
        stable = stableFilt
        
        
        # if decayCheck and not stable:
        
    if method == 'powerRingDecay':
        """
        requires: cutoff, a list of the cutoff frequencies
        optional: startupBuff=7e-9, the time after startup to check decay
                  minPks=3, the minimum numbewr of peaks to determine decay
                  
        """
        
        #### required
        if 'cutoff' in kwargs.keys():
            cutoff = kwargs['cutoff']
            flow = cutoff[0]
            fhigh = cutoff[1]
        else:
            raise Exception("kwarg 'cutoff' is required for checkStability of method '%s'"%(method))
            
        ##### Optional
        if 'startupBuff' in kwargs.keys():
            startupBuff = kwargs['startupBuff']
        else:
            startupBuff=10e-9
        if 'minPks' in kwargs.keys():
            minPks  = kwargs['minPks ']
        else:
            minPks = 3
          
        ######### begin method
        tStart = getStartup(DF,method='bandpass',cutoff=cutoff,hRatio=0.4,pRatio=0.4,debug=debug,fignum=fignum)
        
        if debug:
            fig,ax = plot1D(DF,fig=fignum)
            ax.set(title='Original Signal, tstart=%0.2f ns'%(tStart*1e9))
            fig = drawFig(fig)
            fignum = fignum + 1

        #DF = applyFilter(DF,method='high',cutoff=flow,order=3,axis=-1)

        DFfilt = applyFilter(DF,method='low',cutoff=fhigh,order=3,axis=-1)
        if debug:
            fig,ax = plot1D(DFfilt,fig=fignum)
            ax.set(title='low pass signal')
            fignum = fignum + 1
        
        DFfilt = DFfilt.loc[DFfilt.index.get_level_values(0)>(tStart+startupBuff)]
        DFfilt = DFfilt - DFfilt.mean()
        DFfilt = DFfilt.reset_index()
        # DFfilt['t'] = DFfilt['t'] - DFfilt['t'].min()
        DFfilt = DFfilt.set_index('t')
        DFfilt = DFfilt.abs()
        # DFfilt = DFfilt.pow(2)
        
        if debug:
            fig,ax = plot1D(DFfilt,fig=fignum,clear=True)
        
        
        ###### step 2: check the decay of the beat signal
        # get as many peaks as i can?
        hRatio=None
        pRatio=0.1
        DFpksCheck,propsCheck = findPks(DFfilt,maxPks=30,hRatio=hRatio,pRatio=pRatio)
        
        decayRate = np.nan
        ###### use curve fit on peaks, line
        if (DFpksCheck.shape[0] > minPks):
            
            firstPeak = DFpksCheck.iloc[0][0] # this is the first peak after the startup peak
            y = DFpksCheck[DFpksCheck.columns[0]].to_numpy()                # variable values need to be of similar order
            yNorm = 1/y.max()
            y = y*yNorm
            
            x = DFpksCheck.index.get_level_values(0).to_numpy()   # converted to ns to be similar in order
            xNorm = 1/x.max()
            x = x*xNorm
            curve,pcov = curve_fit(lambda x,m,b:lineEqu(x,m,b),x,y)
            m,b = curve[0],curve[1]         # m [W/ns]
            decayRate = m*xNorm/yNorm/1e9     # [W/ns]
            decayRate = decayRate*yNorm     # [1/ns]
            
            # for sqared signal denormalization
            # m = np.sign(m)*np.sqrt(np.abs(m))
            # b = np.sign(b)*np.sqrt(np.abs(b))
            # yNorm =np.sqrt(yNorm)
            
            
            DFline = pd.DataFrame(lineEqu(x,m,b)/yNorm,x/xNorm,columns=['decay fit'])
            DFline.index.name = 't'
            
            ###### minimum decay compensation for short times
            # need equation for minDecay that approaches minDecay for long times and something much higher for short times
            # equation of capacitor decay voltage.
            
            # this code should be implemented outside checkStable?
            tend = DFfilt.index.get_level_values(0).max() - DFfilt.index.get_level_values(0).min()
            tau = 5e-9
            alpha = 1/tau
            minDecay = 0.01
            maxDecay = 1
            minDecay = (maxDecay-minDecay)*np.exp(-alpha*tend)+minDecay

            if (decayRate <= -minDecay):
                stableDecay = True
            else:
                stableDecay = False
                
            if debug:
                # # for sqared signal denormalization
                # fig,ax = plot1D(DFfiltAbs,fig=fignum,clear=True)
                # fig,ax = scatter(DFpksCheck.pow(1/2),fig=fig,clear=False,color='b')
                
                # for non-sqared signals
                fig,ax = plot1D(DFfilt,fig=fignum,clear=True)
                fig,ax = scatter(DFpksCheck,fig=fig,clear=False,color='b')
                
                fig,ax = plot1D(DFline,fig=fig,clear=False)
                ax.relim()
                ax.autoscale()
                ax.set(title='mod decay [%%/ns]: detect=%0.1f, min=%0.1f, stable=%0.0f'%(-decayRate*100,minDecay*100,stableDecay))
                fig = drawFig(fig)
                fignum = fignum + 1
        
        
        if method == 'powerDecay':
            maxAttenuationFactor = 0.03/10   # [1/ns]
            maxAttenuationRate = maxAttenuationFactor  # [1/ns]
            DFfilt = applyFilter(DF,method='low',cutoff=fhigh,order=3,axis=-1)
            tStart  = DFfilt.idxmax()[0]
            themax = DFfilt.max()[0]
            DFfilt = DFfilt[DFfilt.index.get_level_values(0) > tStart]
            
            if debug:
                fig,ax = plot1D(DF,fig=fignum)
                ax.set(title='Original Signal, tstart=%0.2f ns'%(tStart*1e9))
                fig = drawFig(fig)
                fignum = fignum + 1
    
            
            #####  calculate slope to see linear attenuation of power

            # method 3: fitting a line to the profile itself
            y = DFfilt[DFfilt.columns[0]].to_numpy()                # variable values need to be of similar order
            x = DFfilt.index.get_level_values('t').to_numpy()*1e9   # converted to ns to be similar in order
            if len(y) > 0:
                curve,pcov = curve_fit(lambda x,m,b:lineEqu(x,m,b),x,y)
                m,b = curve[0],curve[1]         # m [W/ns]
                attenuationRate = m/themax            # [1/ns]
                DFline = pd.DataFrame(lineEqu(x,m,b),x/1e9,columns=['fit'])
                DFline.index.name = 't'
                if -attenuationRate > maxAttenuationRate:
                    stableAttenuation = False
                else:
                    stableAttenuation = True

                if debug: 
                    fig,ax = plot1D(DFfilt,fig=fignum)
                    fig,ax = plot1D(DFline,fig=fig,clear=False)
                    ax.set(title='attenuation [%%/ns]: detect=%0.2f, min=%0.2f,stable=%0.0f'%(attenuationRate*100,-maxAttenuationRate*100,stableAttenuation))
                    fig = drawFig(fig)
                    fignum = fignum + 1
            else:
                stableAttenuation = True
        stable = stableAttenuation
        
    return stable


def _checkStabilityOld(DF,method='bandpass',minStart=60e-9,minSteady=10e-9,fftRange=[0.6,1.0],hRatio=None,pRatio=None,debug=False):
    # initialize additional stable checks
    stableDecay = True
    stableAttenuation = True
    
    cutoff = [50e6,500e6]
    decayCheck = True
    minPks = 3  # minimum peaks to check decay rate
    startupBuff = 4e-9
    attenuationCheck = True 
    
    if not type(cutoff) is list:
        cutoff = [cutoff]
      
    tend = DF.index.get_level_values('t').max()
    tStart = getStartup(DF,debug=False)
        
    fignum = 1
    if debug:
        fig,ax = plot1D(DF,fig=fignum)
        ax.set(title='Original Signal, tstart=%0.2f ns'%(tStart*1e9))
        fig = drawFig(fig)
        fignum = fignum + 1
        
    ##### check startup and steady state signal time for minimum requirments
    if minStart:
        if tStart > minStart:
            stable = False
            return stable
        
    if minSteady:
        
        tSteady = tend - tStart
        if tSteady < (minSteady + startupBuff):
            stable = False
            return stable
    

    
    
    
    
    # check decay rate
 
    
        
        ###### fit sinusoid to filtered signal  
        # T = getPeriod(DFfilt,hRatio=hRatio,pRatio=pRatio,debug=debug)
        # if debug:
        #     fig,ax = plot1D(DFfilt,fig=fignum)
        #     ax.set(title='Estimated Beat Period = %0.2f ns'%(T*1e9))
        #     fignum = fignum + 1
            
        
        # phase = getPhase(DFfilt,theSignal='sin',period=None,hRatio=0.4,pRatio=0.3)
        # phase = phase.iloc[0][0]
        
        # xNorm = 1e9      # t normalization
        # y = DFfilt[DFfilt.columns[0]].to_numpy()                # variable values need to be of similar order
        # x = DFfilt.index.get_level_values('t').to_numpy()*xNorm   # converted to ns to be similar in order
        # if len(y) > 0:
        #     f = 1/T/xNorm
        #     w = 2*np.pi/T/xNorm
        #     curve,pcov = curve_fit(lambda x,A,alpha:sineAttenuationEqu(x,A,w,phase,alpha),x,y,bounds=([0.5e6,-2],[np.inf,2]))
        #     alpha = curve[1]        # m [W/ns]
        #     A = curve[0]
        #     # alpha = 0
        #     # A = 2e6
        #     # attenuationRate = m/themax            # [1/ns]
        #     DFline = pd.DataFrame(sineAttenuationEqu(x,A,w,phase,alpha),x/xNorm,columns=['fit'])
        #     DFline.index.name = 't'
        #     # if -attenuationRate > maxAttenuationRate:
        #     #     stable = False
                
            
        # if debug:
        #     fig,ax = plot1D(DFline,fig=fig,clear=False)
        #     # if (DFpksCheck.shape[0] > minPks):
        #     #     fig,ax = plot1D(DFline,fig=fig,clear=False)
        #     ax.relim()
        #     ax.autoscale()
        #     ax.set(title='mod decay [%%/ns]: detect=%0.1f, min=%0.1f, stable=%0.0f'%(-decayRate*100,minDecay*100,stable))
        #     fig = drawFig(fig)
        #     fignum = fignum + 1
            
     
    # check if power is constantly decreasing. filtered DF needs to be renamed. 
    # ill use startup time to ignore the sudden increase
    
    
    return stable

def getBeatPeriod(DF,cutoff=[50e6,500e6],hRatio=0.4,pRatio=0.3,startup=True,debug=False):
    flow = 50e6
    fhigh = 500e6        
    startupBuff = 7e-9
    
    #DF = applyFilter(DF,method='high',cutoff=flow,order=3,axis=-1)
    if type(startup) is bool:
        startup = getStartup(DF,debug=False)
    elif type(startup) is float:
        pass
    else:
        startup = 0.0
            
    DF = applyFilter(DF,method='low',cutoff=fhigh,order=3,axis=-1)
    if debug:
        fig,ax = plot1D(DF,fig=11)
        ax.set(title='filtered signal')
    
    DF = DF.loc[DF.index.get_level_values('t')>(startup+startupBuff)]
    DF = DF - DF.mean()
    T = getPeriod(DF,hRatio=hRatio,pRatio=pRatio,debug=debug)
    if debug:
        fig,ax = plot1D(DF,fig=12)
        ax.set(title='Estimated Beat Period = %0.2f ns'%(T*1e9))

    return T

def getStartup(DF,method='bandpass',cutoff=[50e6,500e6],hRatio=0.4,pRatio=0.4,debug=False,fignum=1):
    # requires output power signal
    if not type(cutoff) is list:
        cutoff = [cutoff]
    

    if method == 'highlow':
        flow = min(cutoff)
        fhigh = max(cutoff)
        DF = applyFilter(DF,method='high',cutoff=flow,order=3,axis=-1)
        if debug: plot1D(DF,fig=fignum)
        DF = applyFilter(DF,method='low',cutoff=fhigh,order=3,axis=-1)
    elif method == 'bandpass':
        flow = min(cutoff)
        fhigh = max(cutoff)
        DF = applyFilter(DF,method='band',cutoff=cutoff,order=3,axis=-1)
        if debug: plot1D(DF,fig=fignum)   
    elif method == 'lowdiff':
        fhigh = max(cutoff)
        DF = applyFilter(DF,method='low',cutoff=fhigh,order=3,axis=-1)
        if debug: plot1D(DF,fig=fignum)
        DF = DF.diff()
    elif method == 'abs':
        DF = DF.abs()
        if debug: plot1D(DF,fig=fignum)
    else:
        if debug: plot1D(DF,fig=fignum)
        
    fignum += 1
    DFpks,props = findPks(DF,maxPks=10,hRatio=hRatio,pRatio=pRatio)
    if debug: 
        fig,ax = plot1D(DF,fig=fignum)
        fig,ax = scatter(DFpks,fig=fig,clear=False,color='b')
        ax.relim()
        ax.autoscale()
        fig = drawFig(fig)
    if not DFpks.empty: startup = DFpks.index[0]
    else: startup = np.nan
    return startup

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

def movAvg(DF,n=100):
    DF = DF.rolling(n).mean()
    if not issubclass(type(DF), pd.core.series.Series): 
        DF.columns = ['movAvg(%s)'%col for col in DF.columns]
    else:
        DF.name = 'movAvg(%s)'%DF.name
 
    return DF.dropna()

def binDF(DF,binVars,bins,inplace=False):
    """
    This bins the DataFrame by the column labeled <var> by the <bins> and the agregation in methods
    bins can be an integer representing the number of bins, or a list of the bin breaks
    Input:
        bins: [integer] the number of bins
              [list of floats]: list of the bin breaks
        methods: [string] name of the method to agregate, function returns groups DF
                 [list of strings]: names of the method to agregate, function returns dictionary
                 
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

def applyFilter(DF,method,cutoff,order=5,axis=-1,modLabels=True):
    '''
    methods = 'low', 'high', 'band'
    
    '''
    
    if not DF.isna().to_numpy().any():
        
        if not issubclass(type(DF), pd.core.series.Series): 
            if modLabels:
                cols = ['%sP(%s)'%(method[0].upper(),col) for col in DF.columns]
            else:
                cols = DF.columns
            if len(cols)>1:
                DF = DF.stack(dropna=False)
                
                #DF.name = 'value'
                if axis==-1: axis = axis-1
        else:
            if modLabels:
                cols = ['%sP(%s)'%(method[0].upper(),DF.name)]
            else:
                cols = [DF.name]
            
        if type(cutoff) is not list: cutoff = [cutoff]
        if method=='band':
            if len(cutoff) != 2:
                raise Exception('with method %s, cutoff must be a list of length 2'%method)
        else:
            if len(cutoff) != 1:
                raise Exception('with method %s, cutoff must be a scaler'%method)
            #cutoff = cutoff[0]
        
        
        array,bounds=DF2Numpy(DF)
        iName = list(bounds.keys())[axis]
        x = bounds[iName]
        
        dx=x[1]-x[0]
        fs = 1/dx
        nyq = 0.5 * fs
        normal_cutoff = [v/nyq for v in cutoff]
        padlen = None #int(array.shape[axis]*0.001)
        sos = signal.butter(order, normal_cutoff, btype=method, analog=False,output='sos')
        array = signal.sosfiltfilt(sos, array,axis=axis,padlen=padlen)
        # array = signal.sosfilt(sos, array,axis=axis)
        DF = numpy2DF(array,bounds)
        if len(cols)>1: DF = DF.unstack()
        DF.columns = cols
    else:
        print('Could not filter signal because of NaN value!')
        DF = DF
        
    return DF

def intervalColumns2Num(DF,inplace=True):
    """
    This converts a pd.series of pd.intervals object to one with floats. 
    Usefull for storing as H5 or plotting 
    """
    if not inplace: DF = copy.deepcopy(DF)
    #AG = AG.reset_index()
    if not issubclass(type(DF), pd.core.series.Series): 
        for i,col in DF.iteritems():
            if type(col.iloc[0])==pd._libs.interval.Interval:
                DF[col.name]=[(x.left+x.right)/2 for x in col]
    else:
        if type(DF.iloc[0])==pd._libs.interval.Interval:
                DF=[(x.left+x.right)/2 for x in DF]
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

    
def lineEqu(x,m,b):
    #y=m*x+b
    return m*x+b

def expEqu(x,m,b):
    #y=m*x+b  PLACEHOLDER, NOT ACCURATE
    return m*x+b

def sineAttenuationEqu(x,A,omega,phase,alpha):
    return A*np.exp(alpha*x)*np.sin(omega*x-phase)

