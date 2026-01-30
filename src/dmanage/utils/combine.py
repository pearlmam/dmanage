# -*- coding: utf-8 -*-


import pandas as pd
from dmanage.utils import objinfo

def combine_dicts(dictList):
    for i,dictionary in enumerate(dictList):
        if i == 0:
            outDict = dictionary
        else:
            for key in dictionary.keys():
                if not type(outDict[key]) is list: outDict[key] = [outDict[key]]
                if not type(dictionary[key]) is list: dictionary[key] = [dictionary[key]]
                outDict[key] = outDict[key] + dictionary[key]
    return outDict

def combine_dfs(dfList,var=None,axis=1):
    """
    combine dicts. right now it is untested with MultiIndex
    """
    if not objinfo.is_container(dfList) or len(dfList) < 2:
        return dfList
    # make a check here
    #df0 = dfList[0]
    # df1 = dfList[1]
    
    if var is None:
        var = {None:range(0,len(dfList[0].columns))}
    if axis == 0:
        iNames = list(var.keys()) + list(dfList[0].index.names)
        index = pd.MultiIndex.from_product([list(var.values())[0],dfList[0].index],names=iNames)
        df = pd.concat(dfList,axis=0)
        df.index = index
    elif axis == 1:
        iNames = list(var.keys()) + list(dfList[0].columns.names)
        index = pd.MultiIndex.from_product([list(var.values())[0],dfList[0].columns],names=iNames)
        df = pd.concat(dfList,axis=1)
        df.columns = index
        
        
    return df
if __name__ == "__main__":
        
    sweepVar = {'sweepVarName':[100,200]}
    
    df0 = pd.DataFrame([[0,0],[1,1]],index=['first','second'],columns=['col1','col2'])
    df0.columns.name = 'columns'
    df0.index.name = 'index'
    df1 = pd.DataFrame([[2,2],[3,3]],index=['first','second'],columns=['col1','col2'])
    df1.columns.name = 'columns'
    df1.index.name = 'index'
    dfs = [df0,df1]
    
    # iNames = list(sweepVar.keys()) + list(df0.columns.names)
    # index = pd.MultiIndex.from_product([range(0,2),dfs[0].columns])
    # df = pd.concat(dfs,axis=1)
    # df.columns = index
    
    df = combine_dfs(dfs,var=sweepVar,axis=0)
    print(df)
