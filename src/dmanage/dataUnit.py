#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:09:02 2021
dataUnit stuff
@author: marcus
"""
import io
# import numpy as np
import pandas as pd
import os
import getpass
import types
import sys
import inspect
# import functools
# from dmanage.loaders import vsim
# import inspect

from dmanage.server.basic import Server


def makeDataUnit(base):
    """ Creates DataUnit class
    :param path: The path of the file to wrap
    This creates the DataUnit class with the inherited components from the base class

    Parameters
    ----------
    base : class
        This is the base class to inheret that consists of the components required for analysis

    Returns
    -------
    class
        This is the DataUnit class with the components.

    """
    
    class DataUnit(base):
        
        def __init__(self,dataPath,computer='local',user=None):
            """Loads components of the DataUnit (folder or file)
            This is the base data unit class which consists of components and methods inhereted from a base class. The base class is unique to each simulation, experiment, or application.

            Parameters
            ----------
            dataPath : str, required
                This is the path to the file or folder
            computer : str, optional
                The ip address or name of the computer where the dataUnit is. The default is 'local'.
            user : str, optional
                The user name credentials for the login if needed. Setup an ssh public and private keys to login to the server, no password option is given here. The default is None.

            Returns
            -------
            None.

            """
            
            if computer != 'local':
                
                self.Server = Server(computer=computer,user=user)
                # list relevant script files
                script=inspect.getframeinfo(sys._getframe(1)).filename
                filename = os.path.basename(script)
                
                # open connection
                self.Server.connect()
                self.Server.put(script,self.Server.workspace+filename)
                # put all relevant scripts on the remote server
                # keep connection open???
                self.Server.close()
                # server_wrap_component_methods
            super().__init__(dataPath)
            # define attributes
            
            self.baseDir = os.path.join(dataPath,'')
            self.resDir = self.baseDir+'processed/'
            self.summaryFile = self.baseDir + 'summary.csv'
            # self.summaryData = pd.Series() # 
            self.summaryData = self.readSummary()
            #vsim.VSimRead(self.baseDir,self)  # ??? There should be a validity check and generic sim loader here
            
        
        
        
        def testServerWrap(self):
            self.Server.connect()
            self.Server.put()
            self.Hists.readAsDF('Pout')
        
        
        def inheritanceLevel():
            return 'DU'
        
        def load(self,dataPath=None,iLevel='DU'):
            # step through inheretanceLevels
            base = self.__class__
            level = base.inheritanceLevel()
            while not (level.lower() == 'du'):
                if len(base.__bases__) < 1:
                    raise Exception("Inheritance chain does not include level '%s'"%level)
                base = base.__bases__[0]
                level = base.inheritanceLevel() 
            return base(dataPath)
        
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
