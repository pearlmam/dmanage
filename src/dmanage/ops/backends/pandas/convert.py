# -*- coding: utf-8 -*-


import numpy as np
import pandas as pd
import gc
import copy
from multiprocess import Pool


def create_bounds(array, iNames, bounds = {}):
    s = array.shape
    if len(iNames) != len(s):
        raise Exception('Length of iNames should be the same as the array dimension')
    index = [range(s)for s in s]
    for key in bounds:
        if any(key in x for x in iNames):
            if str(type(bounds[key])) != str(type([])) and str(type(bounds[key])) != str(np.ndarray):
                raise Exception('Dictionary element "%s" is not of type "list" or "np.ndarray"'%(key))
            i = iNames.index(key)
            if s[i] != len(bounds[key]):
                raise Exception('Length of %s (%i) is not equal to the array dimension (%i)'%(key,len(bounds[key]),s[i]))
            index[i] = bounds[key]
    newBounds = {iName:index[i] for i,iName in enumerate(iNames)}
    return newBounds

def replace_bound(bounds, oldKey, newKey, val=None):
    # sets the index of oldIname to newIName with iVals
    bounds = {newKey if key==oldKey else key:value for key,value in bounds.items()}
    if type(val) != type(None):
        bounds[newKey] = val
    return bounds


def replace_bounds(bounds, oldKeys, newKeys, vals=None):
    if type(oldKeys) != list: oldKeys = [oldKeys]
    if type(newKeys) != list: newKeys = [newKeys]
    if (type(vals) == None) or (type(vals) != list): vals = [vals]*len(oldKeys)
    lens = [len(oldKeys),len(newKeys),len(vals)]
    if all(l!=lens[0] for l in lens): raise Exception('Length of oldKeys, newKeys, and vals must be equal')
    
    newBounds = {}
    for (key,val) in bounds.items():
        if key in oldKeys:
            i = oldKeys.index(key)
            if type(vals[i]) != None: newBounds[newKeys[i]]=vals[i]
            else: newBounds[newKeys[i]]=bounds[oldKeys[i]]
        else: newBounds[key]=val
    return newBounds


def numpy_to_df(array, bounds, colName='value', inplace=False):
    """
    Convert from numpy array to pandas dataframe. each dimension is an index with the values representing the data.
    
    Parameters
    ----------
    array : numpy array 
        array can be any dimension
    iNames : list of strings 
        representing the names of each dimension of array the length of iNames should be equal to the array dimension
    colNames : string  
        represents the data name and will be the column name
    ibounds : Dictionary, optional
        represents the bounds of the array. each dictionary element name needs to corespond to an iName whose
        value is a list of the same length of the dimension. These will be the index values

    Returns
    -------
    DF : DataFrame
        The DataFrame will have indexes with the same number of levels as the array dimensions
        The index values will be determined from ibounds, if defined, otherwise they will be integers
        
    """
    if type(colName) is not list: colName = [colName]
    s = array.shape 
    iNames = list(bounds.keys())
    vals = [v for k,v in bounds.items()]
    if len(s) > 1:
        index = pd.MultiIndex.from_product(vals, names=iNames[0:len(s)])
    else:
        index = pd.Index(vals[0],name=iNames[0])
    
    DF = pd.DataFrame({colName[0]: array.flatten()}, index=index)
    DF.columns=colName
    #DF.index.names = bounds.keys()[0:len(s)]
    # DF = DF.reset_index()
    if  inplace == True:
        del(array)
        gc.collect()
    return DF

def df_to_numpy(DF, sort_index=False, inplace=False):
    """
    Convert from  pandas dataframe to numpy array.

    Parameters
    ----------
    DF : DataFrame
        pandas DataFrame with the indexes representing the dimensions of the array. DataFrame be Series


    Returns
    -------
    array : numpy array
        The array will have the dimensionality of the index levels
    bounds : Dictionary
        The dictionary with elements representing the index names and values corresponding to the bounds
        since python 3.7, dictionaries are ordered, otherwise an ordered dictionary from collections should be used
        to access the bounds by index, rather by name, use 'bounds[list(bounds)[i]]', where i is the index
        
    """
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column. You may stack the columns creating an additional index (dimension) to ge the function to work")
        else:
            name = DF.columns[0]
    else:
        name = DF.name
        
    bounds = {}
    s = []
    for i,iName in enumerate(DF.index.names):
        # bounds[iName] = DF.index.get_level_values(i).unique().to_numpy()
        bounds[iName] = DF.index.get_level_values(i).unique().to_numpy()
        s = s + [bounds[iName].shape[0]]
    array = np.reshape(DF.to_numpy(),s)
    if  inplace == True:
        del(DF)
        gc.collect()    
    return array,bounds

def cart_to_cyl_vector(DF, vecIndex='v', phiIndex='phi', phiRange='2pi'):
    # v=0 is rho v=1 is phi
    DF.columns.name = 'data'
    if vecIndex in DF.index.names:
        if DF.index.names[-1] != vecIndex:
            iNames = list(DF.index.names)
            iNames.append(iNames.pop(iNames.index(vecIndex)))
            DF = DF.reorder_levels(iNames)
    else:
        raise Exception("%s is not in the index"%vecIndex)
    
    if type(phiIndex) != type(None):
        if phiIndex in DF.columns:
            tempCols = list(DF.columns)
            tempCols.remove(phiIndex)
            phi = copy.deepcopy(DF[phiIndex].unstack()[0])
            DF = DF[tempCols].unstack().reorder_levels([vecIndex,'data'],axis=1)
            DF[phiIndex] = phi
            setPhiIndex = False
        elif phiIndex in DF.index.names:
            DF = DF.unstack().reorder_levels([vecIndex,'data'],axis=1).reset_index(phiIndex)
            setPhiIndex = True
        else:
            raise Exception("%s is not in the index or columns"%phiIndex)
        
    else:
        # attempt to create the phi index from x and y positions
        setPhiIndex = False
        phiIndex = 'phi'
        rIndex = 'r'
        DF = DF.unstack().reorder_levels([vecIndex,'data'],axis=1)
        DF[phiIndex] = np.arctan2(DF.index.get_level_values('y').to_numpy(), DF.index.get_level_values('x').to_numpy())
        DF[rIndex] = np.sqrt(DF.index.get_level_values('y').to_numpy()**2 + DF.index.get_level_values('x').to_numpy()**2)
        
    cosPhi = np.cos(DF[phiIndex].to_numpy())
    sinPhi = np.sin(DF[phiIndex].to_numpy())
    x = copy.deepcopy(DF[0])
    DF[0] = x.mul(cosPhi,axis=0) + DF[1].mul(sinPhi,axis=0) # rho
    DF[1] = -x.mul(sinPhi,axis=0) + DF[1].mul(cosPhi,axis=0) # phi
    DF = DF.set_index(phiIndex,append=True).reorder_levels(['data',vecIndex],axis=1).stack()
    if not setPhiIndex:
        DF = DF.reset_index(phiIndex)
        # DF = DF.set_index(phiIndex,append=True).reorder_levels(['data',vecIndex],axis=1).stack()
    
    # else:
        
        # DF = DF.drop(phiIndex,axis=1).reorder_levels(['data',vecIndex],axis=1).stack() # why? for attempt to create the phi index from x and y positions
        #DF = DF.drop(phiIndex,axis=1).reorder_levels(['data',vecIndex],axis=1).stack()
    
    if phiRange == '2pi':
        DF[phiIndex] = (DF[phiIndex]%(2*np.pi))
    elif phiRange == '2pi/pi':
        DF[phiIndex] = (DF[phiIndex]%(2*np.pi))/np.pi
    elif phiRange == 'pi':
        DF[phiIndex] = (DF[phiIndex]+np.pi)%(2*np.pi) - np.pi
    
    return DF

def mi_to_index(DF, inplace=False):
    if type(DF.index) == pd.core.indexes.multi.MultiIndex:
        if len(DF.index.names)==1:
            iName = DF.index.names[0]
            if inplace:
                DF.reset_index(inplace=inplace)
                DF.set_index(iName,inplace=inplace)
            else: 
                DF = DF.reset_index().set_index(iName)
                
        else: raise Exception('MultiIndex has more than 1 level and cannot be converted to a single index')
    return DF

def interval_to_num_index(DF):
    """
    This converts a pd.series of pd.intervals object to one with floats. 
    Usefull for storing as H5 or plotting 
    It needs to be a uniform DF 
    """
    
    if issubclass(type(DF),pd.core.series.Series): 
        DF = DF.to_frame()
        
    index = DF.index
    if type(index) == pd.core.indexes.multi.MultiIndex:
        for i,iName in enumerate(index.names):
            # if type(index.get_level_values(i)) == pd.core.indexes.interval.IntervalIndex:
            #     This is attempt to set the index without a uniform array
            #     newIndex = index.get_level_values(i).values.left
                
            #     index = index.set_levels(newIndex,level=i,verify_integrity=False)
            if type(index.get_level_values(i)[0]) == pd._libs.interval.Interval:
                newIndex = [interval.left for interval in index.get_level_values(i).unique()]
                index = index.set_levels(newIndex,level=i)
    else:  # type(index) == pd.core.indexes.category.CategoricalIndex:
        if type(index[0]) == pd._libs.interval.Interval:
                name = index.name
                newIndex = [interval.left for interval in index.unique()]
                index = pd.Index(newIndex)
                index.name = name
    DF = DF.set_index(index)
    return DF

def make_structured(DF, cols, bins=50):
    if type(cols) != list:
        cols = [cols]
    if not type(bins) is list:
        bins = [bins]*len(cols)
        
    if len([(True) for col in cols if col in DF.columns]) != len(cols): 
        if len([(True) for col in cols if col in DF.index.names]) == len(cols): 
            iNames = list(DF.index.names)
            DF = DF.reset_index(cols)
        else:
            raise Exception("%s is not found in columns or index, aborting"%cols)
    for i,col in enumerate(cols):        
        DF[col] = pd.cut(DF[col],bins[i])
        
    DF = DF.groupby(iNames).mean()
    DF = interval_to_num_index(DF)
    DF = DF.sort_index()
    return DF


def cyl_to_cart(DF, xyCols=['r', 'phi'], uxyCols = ['ur', 'uphi']):
    """
    converts a datalist from cartesian to cylindrical coordinates
    needs implementation for converting multiIndex from cart to cyl
    and vectors might need a convert
    """
    if type(uxyCols) == type(None):
        uxyCols = []
    if len([(True) for uxyCol in uxyCols if uxyCol in DF.columns]) != 2: 
        if len(uxyCols) != 0: print("%s are not columns, ignoring"%uxyCols)
        uxyCols = []
        newUxyCols ={}
    else: newUxyCols = {uxyCols[0]:'ux',uxyCols[1]:'uy'} 
    newXYCols = {xyCols[0]:'x',xyCols[1]:'y'} 
    newCols = {**newXYCols,**newUxyCols}
    # newCols = {'x':'r','y':'phi','ux':'ur','uy':'uphi'}   
    cols = xyCols + uxyCols
    iNames = False
    if len([(True) for col in cols if col in DF.columns]) != len(cols): 
        if len([(True) for col in cols if col in DF.index.names]) == len(cols): 
            iNames = list(DF.index.names)
            for i,iName in enumerate(iNames):
                if iName in  newCols.keys():
                    iNames[i] = newCols[iName]
            DF = DF.reset_index(cols)
        else:
            raise Exception("%s is not found in columns or index, aborting"%cols)
    
    DFtemp=copy.deepcopy(DF[cols])
    cosPhi = np.cos(DFtemp[xyCols[1]])
    sinPhi = np.sin(DFtemp[xyCols[1]])
    
    DF.rename(columns=newXYCols,inplace=True)
              
    DF['x'] = DFtemp[xyCols[0]] * cosPhi
    DF['y']  = DFtemp[xyCols[0]] * sinPhi
    if len(uxyCols) == 2: 
        DF.rename(columns=newXYCols,inplace=True)
        rVphi = DFtemp[xyCols[0]]*DFtemp[xyCols[1]]
        DF['ux'] = DFtemp[uxyCols[0]]*cosPhi - rVphi*sinPhi
        DF['uy'] = DFtemp[uxyCols[0]]*sinPhi - rVphi*cosPhi
    if iNames:
        if type(DF.index) == pd.core.indexes.range.RangeIndex: 
            append=False
        else: 
            append=True
        DF = DF.set_index(list(newCols.values()),append=append).reorder_levels(iNames).sort_index()
    
    return DF


def cart_to_cyl(DF, xyCols=['x', 'y'], uxyCols = ['ux', 'uy'], rphiCols=['r', 'phi'], phiRange='2pi', nc=1):
    '''
    paralell process often takes longer.
    '''
    if nc > 1:
        DFs = np.array_split(DF,nc)
        variables = [(DF,xyCols,uxyCols,rphiCols,phiRange) for DF in DFs]
        pool = Pool(processes=nc)
        F =  pool.starmap_async(_cart_to_cyl, variables)
        DFs = F.get()
        pool.close()
        DF = pd.concat(DFs,axis=0)
    else:
        DF = _cart_to_cyl(DF, xyCols=xyCols, uxyCols=uxyCols, rphiCols=rphiCols, phiRange=phiRange)
    return DF
        

def _cart_to_cyl(DF, xyCols=['x', 'y'], uxyCols = ['ux', 'uy'], rphiCols=['r', 'phi'], phiRange='2pi'):
    """
    converts a dataFrame from cartesian to cylindrical coordinates
    needs implementation for converting multiIndex from cart to cyl
    and vectors might need a convert
    
    To Do: the order of the columns for the inplace=False method should be in the same order.
    """
    if type(uxyCols) == type(None):
        uxyCols = []
    if len([(True) for uxyCol in uxyCols if uxyCol in DF.columns]) != 2: 
        if len(uxyCols) != 0: print("%s are not columns, ignoring"%uxyCols)
        uxyCols = []
        newUxyCols ={}
    else: newUxyCols = {uxyCols[0]:'ur',uxyCols[1]:'uphi'} 
    newXYCols = {xyCols[0]:rphiCols[0],xyCols[1]:rphiCols[1]} 
    newCols = {**newXYCols,**newUxyCols}
    # newCols = {'x':'r','y':'phi','ux':'ur','uy':'uphi'}   
    cols = xyCols + uxyCols
    phiCol = rphiCols[1]
    iNames = False
    if len([(True) for col in cols if col in DF.columns]) != len(cols): 
        if len([(True) for col in cols if col in DF.index.names]) == len(cols): 
            iNames = list(DF.index.names)
            for i,iName in enumerate(iNames):
                if iName in  newCols.keys():
                    iNames[i] = newCols[iName]
            DF = DF.reset_index(cols)
        else:
            raise Exception("%s is not found in columns or index, aborting"%cols)
    
    DFout=copy.deepcopy(DF.loc[:,cols])
    DFout.rename(columns=newXYCols,inplace=True)
    DFout[rphiCols[0]] = np.sqrt(DF.loc[:,xyCols[0]]**2 + DF.loc[:,xyCols[1]]**2)
    DFout[rphiCols[1]]  = np.arctan2(DF[xyCols[1]],DF[xyCols[0]])
    if len(uxyCols) == 2:
        DFout.rename(columns=newUxyCols,inplace=True)
        DFout['u'+rphiCols[0]] = (DF[xyCols[0]]*DF[uxyCols[0]] + DF[xyCols[1]]*DF[uxyCols[1]])/DFout[rphiCols[0]]
        DFout['u'+rphiCols[1]] = (DF[xyCols[0]]*DF[uxyCols[1]] - DF[uxyCols[0]]*DF[xyCols[1]])/DFout[rphiCols[0]]**2
    DF = DF.drop(cols,axis=1,inplace=False)
    DFout = pd.concat([DFout,DF],axis=1)
    if iNames:
        DFout = DFout.set_index(list(newCols.values()),append=True).reorder_levels(iNames).sort_index()
    DFout = convert_phi_range(DFout, phiRange=phiRange, phiCol=phiCol)
    return DFout
    

def rotate_cyl(DF, theta=0, phiCol='phi', discretePhi=False, phiRange='2pi', interpolate=True, nc=1):
    
    if nc > 1:
        DFs = np.array_split(DF,nc)
        thetas = np.array_split(theta,nc)
        variables = [(DF,theta,phiCol,discretePhi,phiRange,interpolate) for DF,theta in zip(DFs,thetas)]
        pool = Pool(processes=nc)
        F =  pool.starmap_async(_rotate_cyl, variables)
        DFs = F.get()
        pool.close()
        DF = pd.concat(DFs)
    else:
        DF = _rotate_cyl(DF, theta=theta, phiCol=phiCol, discretePhi=discretePhi, phiRange=phiRange, interpolate=interpolate)
    
    return DF

def _rotate_cyl(DF, theta=0, phiCol='phi', discretePhi=False, phiRange='2pi', interpolate=True):
    iNames = False
    if not issubclass(type(DF), pd.core.series.Series):
        if not phiCol in DF.columns:
            if  phiCol in DF.index.names:
                iNames = list(DF.index.names)
                DF = DF.reset_index(phiCol)
            else:
                raise Exception("%s is not found in columns or index, aborting"%phiCol)
    else:
        if phiCol in DF.index.names:
            iNames = list(DF.index.names)
            DF = DF.reset_index(phiCol)
            
    n = len(DF[phiCol].unique())
    DF[phiCol] = DF[phiCol] + (theta)

    DF[phiCol] = ((DF[phiCol]+2*np.pi)%(2*np.pi)) # convert to 2pi range
    # phiValues = DF[phiCol].unique()
    piFactor = 2*np.pi    # phi values are from 0 to almost pi
    if discretePhi:
        # floor or ceil is used instead of round to prevent values rounding to the same value and having repeat values, doesnt work
        # DF[phiCol] = np.round(DF[phiCol]*(n)/2/np.pi)*2*np.pi/(n+1)   # old
        DF[phiCol] = (np.round(DF[phiCol]*(n)/piFactor)%n)*piFactor/(n)
        #DF[phiCol].iloc[DF[phiCol]==np.pi*2]=0
        # DF = DF.drop_duplicates('phi')   # need to drop duplicate values in order to unstack
        # will need to make uniform if plotting
        DF = DF.set_index(phiCol,append=True)
        DF = make_uniform_df(DF, interpolate=interpolate)   # with rotating grid fields, this operation takes a lot of memory, I may need to shrink dataset, ie: bin, group, and average
        DF = DF.reset_index(phiCol)
        
    if phiRange == '2pi':
        DF[phiCol] = ((DF[phiCol]+2*np.pi)%(2*np.pi))
    elif phiRange == '2pi/pi':
        DF[phiCol] = ((DF[phiCol]+2*np.pi)%(2*np.pi))/np.pi
    elif phiRange == 'pi':
        DF[phiCol] = (DF[phiCol]+np.pi)%(2*np.pi) - np.pi
        
    if iNames:
        DF = DF.set_index(phiCol,append=True).reorder_levels(iNames).sort_index()
    return DF

def convert_phi_range(DF, phiRange='2pi', phiCol='phi'):
    if not phiCol is None:
        if phiCol in DF.columns:
            if phiRange == '2pi':
                DF[phiCol] = ((DF[phiCol]+2*np.pi)%(2*np.pi))
            elif phiRange == '2pi/pi':
                DF[phiCol] = ((DF[phiCol]+2*np.pi)%(2*np.pi))/np.pi
            elif phiRange == 'pi':
                DF[phiCol] = (DF[phiCol]+np.pi)%(2*np.pi) - np.pi
        elif phiCol in DF.index.names:
            indexNames = list(DF.index.names)
            DF = DF.reset_index(phiCol)
            if phiRange == '2pi':
                DF[phiCol] = ((DF[phiCol]+2*np.pi)%(2*np.pi))
            elif phiRange == '2pi/pi':
                DF[phiCol] = ((DF[phiCol]+2*np.pi)%(2*np.pi))/np.pi
            elif phiRange == 'pi':
                DF[phiCol] = (DF[phiCol]+np.pi)%(2*np.pi) - np.pi
            DF = DF.set_index(phiCol,append=True)
            DF = DF.reorder_levels(indexNames)
            
    else:
        if phiRange == '2pi':
            DF = ((DF+2*np.pi)%(2*np.pi))
        elif phiRange == '2pi/pi':
            DF = ((DF+2*np.pi)%(2*np.pi))/np.pi
        elif phiRange == 'pi':
            DF = (DF+np.pi)%(2*np.pi) - np.pi

    return DF.sort_index()


def rotate_cart(DF, theta=0, xyCols = ['x', 'y'], discretePos=False):
    iNames = False
    if len([(True) for xyCol in xyCols if xyCol in DF.columns]) != 2: 
        if len([(True) for xyCol in xyCols if xyCol in DF.index.names]) == 2: 
            iNames = list(DF.index.names)
            DF = DF.reset_index(xyCols)
        else:
            raise Exception("%s is not found in columns or index, aborting"%xyCols)
    if discretePos:
        xBreaks = DF[xyCols[0]].unique()
        yBreaks = DF[xyCols[1]].unique()
        dx = xBreaks[1]-xBreaks[0]
        dy = yBreaks[1]-yBreaks[0]
        xBreaks = np.append(xBreaks-dx,xBreaks[-1]+dx)
        yBreaks = np.append(yBreaks-dy,yBreaks[-1]+dy)
    
    x = copy.deepcopy(DF[xyCols[0]].to_numpy())
    DF[xyCols[0]] = x*np.cos(theta) - DF[xyCols[1]]*np.sin(theta)
    DF[xyCols[1]] = x*np.sin(theta) + DF[xyCols[1]]*np.cos(theta)
    
    
    if discretePos:
        DF['x'] = pd.cut(DF['x'],xBreaks)
        DF['y'] = pd.cut(DF['y'],yBreaks)
        
    if iNames:
        DF = DF.set_index(xyCols,append=True).reorder_levels(iNames).sort_index()
    
    return DF

def make_uniform_df(DF, method=None, fill_value=np.nan, interpolate=True, limit_area='inside'):
    # this will make the data uniform and interpolate inside nan values, igonres end nan values
    vector = False
    
    if not type(DF.index) == pd.core.indexes.multi.MultiIndex: return DF
    DF = DF[~DF.index.duplicated()]  # get rid of duplicate indecies because it wont be uniform??
    
    levels = DF.index.names
    indexList = []
    for level in levels:
        indexList = indexList + [DF.index.get_level_values(level).unique()]
    
    mi = pd.MultiIndex.from_product(indexList)
    DF = DF.reindex(mi,fill_value=fill_value)
    # interpolate
    # DF1 = copy.deepcopy(DF)
    iNames = list(mi.names)
    if 'v' in iNames:
        # this is a vector and needs special treatment 
        vector = True
        DF = DF.unstack('v')
        iNames.remove('v')
    if interpolate:
        for i,level in enumerate(iNames):
            if limit_area:
                # DF = DF.unstack(level).interpolate(method='linear',limit_area=limit_area).stack(dropna=False)
                DF = DF.unstack(level).interpolate(method='linear',limit_area=limit_area).stack(future_stack=True)
                
            else:
                # print(DF.unstack(level))
                # DF = DF.unstack(level).interpolate(method='linear').stack(dropna=False)
                DF = DF.unstack(level).interpolate(method='linear').stack(future_stack=True)
                # print(DF.unstack(level))
    if vector:
        DF = DF.stack(dropna=False)
    
    # print(DF)
    return DF


def interval_to_num_columns(DF, inplace=True):
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


if __name__ == "__main__":
    a = np.linspace(1,0,10)
    t = np.linspace(0, 10, 1000)
    A,T = np.meshgrid(a,t)
    Y = A*np.sin(2*np.pi*T) # something there
    df = pd.DataFrame(Y, columns=a, index=t)
    df.columns.name = 'Amplitude'
    df.index.name = 'Time'
    df = df.stack()
    print(df)
    array,bounds = df_to_numpy(df)


