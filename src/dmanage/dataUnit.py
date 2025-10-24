#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:09:02 2021
DataDir stuff
@author: marcus
"""
import io
# import numpy as np
import pandas as pd
import os
# import functools
# from dmanage.loaders import vsim
# import inspect


def makeDataUnit(base):
    class DataUnit(base):
        """
        alternate naming: DataUnit, DataRun, 
            
        """
        def __init__(self,dataDir=None,server='local'):
            super().__init__(dataDir)
            # define attributes
            
            self.baseDir = os.path.join(dataDir,'')
            self.resDir = self.baseDir+'processed/'
            self.summaryFile = self.baseDir + 'summary.csv'
            # self.summaryData = pd.Series() # 
            self.summaryData = self.readSummary()
            #vsim.VSimRead(self.baseDir,self)  # ??? There should be a validity check and generic sim loader here
        
        def inheritanceLevel():
            return 'DU'
        
        def load(self,dataDir=None,iLevel='DU'):
            # step through inheretanceLevels
            base = self.__class__
            level = base.inheritanceLevel()
            while not (level.lower() == 'du'):
                if len(base.__bases__) < 1:
                    raise Exception("Inheritance chain does not include level '%s'"%level)
                base = base.__bases__[0]
                level = base.inheritanceLevel() 
            return base(dataDir)
        
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
        
    return DataUnit