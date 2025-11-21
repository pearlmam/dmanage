#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 22 11:48:20 2025

@author: marcus
"""
import numpy as np
import pandas as pd
import time
from pathos.multiprocessing import Pool

from test_dataDir import MyDataDir
from dmanage.group import make_data_group

SweepDir = make_data_group(MyDataDir)
class MySweepDir(SweepDir):
    # def __init__(self,dataDir=None):
    #     #super().__init__(dataDir
    #     pass

    def getHistory(self,histNames,varDepth=3,nc=1):
        print('Getting Histories: %s...'%histNames, end=' ')
        startTime = time.time()
        nc = min(len(self.sweepDirs),nc)
        if nc > 1:
            sweepDirss = np.array_split(self.sweepDirs,nc)
            variables = [(histNames,sweepDirs,varDepth) for sweepDirs in sweepDirss]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._getHistory,variables)
            result.wait()
            DF = result.get()
            pool.close()
            DF = pd.concat(DF, axis=1)
        else:
            DF = self._getHistory(histNames,varDepth=varDepth)
        
        executionTime = time.time()-startTime
        print('Done in %0.3f seconds'%executionTime)
        return DF
    
    def _getHistory(self,histNames,sweepDirs=None,varDepth=3):
        if not type(histNames) is list:
            histNames = [histNames]
        if sweepDirs is None:
            sweepDirs = self.sweepDirs
        """
        varDepth: for column naming
        """
        DFs = []
        for sweepDir in sweepDirs:
            DD = MyDataDir(self.baseDir + sweepDir)
            DF = DD.Hists.read_as_df(histNames)
            sweepVars = self.getVarsFromDir(sweepDir,dtype='dataframe',Nrepeat=1,depth=varDepth)
            histNameI = pd.DataFrame({'histName':histNames})
            I = pd.concat([histNameI,sweepVars],axis=1).fillna(method='ffill')
            DF.columns = pd.MultiIndex.from_frame(I)
            DFs = DFs + [DF]
        DFs = pd.concat(DFs,axis=1)
        DFs = DFs.sort_index(axis=1)
        return DFs

    def getVarsFromDir(self,folder,dtype='DataFrame',Nrepeat=1,depth=10):
        if self.baseDir in folder: folder=folder.replace(self.baseDir,'')
        folder = folder.rstrip('/')
        varNames = folder.split('/')[-depth:]
        Dict = {}
        for varName in varNames:
            temp = varName.split('-',1)   # only split first occurance
            if len(temp) == 2:
                name = temp[0]
                value = temp[1]
                try: value = float(value)
                except: pass
                Dict[name]=[value]*Nrepeat
            else:
                pass # not a variable or proper format
        if dtype.lower() == 'dict':
            return Dict
        elif dtype.lower() == 'list':
            return list(Dict.keys()),list(Dict.values())
        else:
            return pd.DataFrame(Dict)



if __name__ == "__main__":
    folder = '../test_data/vsim_data/'
    SD = MySweepDir(folder)
    names = ['Pout']
    # data = SD.Hists.readAsDF(names)
    data = SD.getHistory(names)
    
    names = ['Pout', 'VDC', 'electronsIanode']
    
    #scalarVars = SD.getScalarVars(names)