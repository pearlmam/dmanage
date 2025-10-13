#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:09:02 2021
DataDir stuff
@author: marcus
"""
import io
import numpy as np
import pandas as pd
import os

from dmanage import dfmethods as dfm
from dmanage.loaders import vsim  # this needs to change to be more generic


class DataDir(vsim.VSim):
    """
    opens a VSim data directory for common analysis I use. Plotting relevant histories, plotting electrons, stuff like that
    This is the first step to analysing the data directory. You may open up the H5 files directly to access the data
    for uncommon analysis, but I like the structure of this. 
    
    Inputs:
        dataDir: <string>, path to the data directory
        relHAPlots: <Dict>, the format must look like this: { plotTitle:{'histNames':histNames, 'movAvg':movAvg, 'ylabel':ylabel }
                  if an entry is excluded, no error is thrown until you use that entry}
        
    """
    def __init__(self,dataDir=None,simType=None,fullLoad=True):
        super().__init__(dataDir)
        self.debug = True
        self.cmapPhase = 'twilight'
        if (not dataDir is None) and fullLoad:
            self.baseDir = os.path.join(dataDir,'')
            self.resDir = self.baseDir+'processed/'
            self.summaryFile = self.baseDir + 'summary.csv'
            # self.summaryData = pd.Series() # 
            self.summaryData = self.readSummary()
            #vsim.VSimRead(self.baseDir,self)  # ??? There should be a validity chack and generic sim loader here
            
    
    def addDataToSummary(self,data,summaryData=None,internalSummary=True):
        
        if summaryData is None:
            summaryData = self.summaryData
        if type(summaryData) is pd.core.frame.Series:
            summaryData = pd.DataFrame(summaryData).T
        if type(summaryData ) is pd.core.frame.DataFrame:
            if summaryData.shape[0] > 1:
                summaryData  = summaryData .T
        if type(data) is dict:
            datas = []
            for key, value in data.items():
                datas = datas + [pd.DataFrame(pd.Series({key:value})).T]
            if len(datas)>0: data = pd.concat(datas,axis=1)
            else: data = pd.DataFrame()
            # data = pd.Series(data)
            # data = pd.DataFrame(data,index=[0],copy=False)
            #data = pd.DataFrame(pd.Series(data)).T
        if type(data) is pd.core.frame.DataFrame:
            if data.shape[0] > 1:
                data = data.T
        if type(data) is pd.core.frame.Series:
            data = pd.DataFrame(data).T
        if not data.empty:
            for indice in data.index:
                if type(data.loc[indice]) is pd.core.frame.DataFrame:
                    if not type(data.loc[indice].index) is pd.core.indexes.range.RangeIndex:
                        data[indice] = data.loc[indice].reset_index()
            summaryData = pd.concat([summaryData.reset_index(drop=True),data.reset_index(drop=True)],axis=1,ignore_index=False)
            summaryData = summaryData.loc[:,~summaryData.columns.duplicated(keep='last')]
            if internalSummary:
                self.summaryData = summaryData
        return summaryData
    
    def saveSummary(self,saveType = 'csv'):
        #### put all DataFrame data at the end
        self.summaryData = self.summaryData[self.summaryData.dtypes.sort_values().index]
        
        if saveType == 'excel':
            self.summaryData.to_excel(self.summaryFile)
        else:
            self.summaryData.to_csv(self.summaryFile) 
        
    def readSummary(self,ow=False,debug=False):
        if os.path.exists(self.summaryFile) and not ow:
            self.summaryData = pd.read_csv(self.summaryFile)
            self.summaryData = self.summaryData.drop(self.summaryData.columns[0],axis=1)
        else:
            # self.summaryData = pd.Series()
            self.summaryData = pd.DataFrame()
            
        #### check for DataFrame Strings (NOT NEEDED ??????)
        for col in self.summaryData.columns:
            # float(self.summaryData.loc[col][0])
            if type(self.summaryData[col][0]) is str:
                #### attempt to make it a DataFrame
                if '\n' in self.summaryData[col][0]:
                    try: 
                        value = pd.read_csv(io.StringIO(self.summaryData[col][0]),delim_whitespace=True)
                        #value = value.set_index(value.columns[0])
                        self.summaryData[col].loc[0] = value
                    except:
                        if debug:
                            print('Unable to Coerce %s  to Dataframe'%(col))
        return self.summaryData