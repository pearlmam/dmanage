#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:14:34 2021
SweepDir
@author: marcus
"""
import os
import time
import pandas as pd
from multiprocessing import Pool
import natsort
from dmanage.dataDir import DataDir
import dmanage.dfmethods as dfm

class SweepDir(DataDir):
    """
    opens a sweep data directory containing VSim data directories for common analysis I use. 
    Plotting relevant histories, plotting electrons, sweep data, etc
    Can generate a data managment lookup spreadsheet to visualize the availiable data directories
    
    Inputs:
        baseDir: <string>, path to the data directory
        relHAPlots: <Dict>, the format must look like this: { plotTitle:{'histNames':histNames, 'movAvg':movAvg, 'ylabel':ylabel }
                  if an entry is excluded, no error is thrown until you use that entry}
        
    """
    
    def __init__(self,baseDir,simType=None,baseNameDepth=3):
        # sweep data directories
        print('Opening %s...'%baseDir, end = ' ')
        startTime = time.time()
        self.baseDir = os.path.join(baseDir,'')

        self.sweepDirs = self.getDDs(baseDir,nc=1)
        if len(self.sweepDirs) == 0: raise Exception("There are no Data Directories in '%s'"%self.baseDir)
        self.sweepDirs = natsort.natsorted(self.sweepDirs)
        #self.DD = dataDir.DataDir(self.baseDir+self.sweepDirs[0])

        self.resDir = self.baseDir + 'processed/' # result directory
        self.sweepResDir = self.resDir + 'sweep/'
        self.sweepDataSaveName = 'sweepData'
        self.saveType = 'png'
        self.debug = False
        self.dataLookupFile = self.baseDir + 'dataLookup.xlsx'
        self.baseNameDepth=3
        # remove processed directory from list
        try: self.sweepDirs.remove('processed')
        except: pass
        executionTime = time.time()-startTime
        print('Done in %0.3f Seconds'%executionTime)


    
    def _getDDs(self,subDirs):
        sweepDirs = []
        # print(subDirs)
        remDirStrings = ['processed']
        if type(subDirs) != list: subDirs = [subDirs]
        for root in subDirs:
            # print(root)
            skip = False
            for remDirString in remDirStrings:
                if remDirString in root:
                    skip = True
            
            if self.isValid(root) and not skip: sweepDirs.append(root.replace(self.baseDir,''))
            else: pass
            
        return sweepDirs
        
    def getDDs(self,baseDir=None,nc=1):
        
        if type(baseDir) == type(None):
            baseDir = self.baseDir
        subDirs = list(list(zip(*os.walk(baseDir,followlinks=True)))[0])
        # print(type(subDirs))
        if nc > 1:
            pool = Pool(processes=nc)
            result = pool.map_async(self._getDDs,subDirs)
            result.wait()
            sweepDirsList = result.get()
            pool.close()
            sweepDirs = [x for l in sweepDirsList for x in l]  
        else:
            sweepDirs = self._getDDs(subDirs)

        return sweepDirs
        
    def genBaseName(self,theInput,depth=10):
        """
        theInput can be of type string or dict
        """
        if type(theInput) is str:
            if self.baseDir in theInput: theInput=theInput.replace(self.baseDir,'')
            theInput = theInput.rstrip('/')
            theInput = theInput.split('/')[-depth:]
            baseName = '_'.join(theInput)
            # baseName = theInput.replace('/','_')  
        elif type(theInput) is dict:
            baseName = ''
            for name,value in theInput.items():
                baseName = baseName + '_%s-%s'%(name,value)
            baseName = baseName[1:]
        elif issubclass(type(theInput), pd.core.frame.DataFrame):
            pass
        elif issubclass(type(theInput), pd.core.indexes.multi.MultiIndex):
            names = theInput.names
            
        return baseName
    
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
    
    def getVarsFromMI(self,mi,dtype='DataFrame'):
        iNames = mi.names
        Dict = {} 
        for iName in iNames:
            Dict[iName] = list(mi.get_level_values(iName))
            
        if dtype == 'Dict':
            return Dict
        elif dtype == 'List':
            return list(Dict.keys()),list(Dict.values())
        else:
            return pd.DataFrame(Dict)
        
        
    def combineDicts(self,dictList):
        for i,dictionary in enumerate(dictList):
            if i == 0:
                outDict = dictionary
            else:
                for key in dictionary.keys():
                    if not type(outDict[key]) is list: outDict[key] = [outDict[key]]
                    if not type(dictionary[key]) is list: dictionary[key] = [dictionary[key]]
                    outDict[key] = outDict[key] + dictionary[key]
        return outDict
    
    def getVarsFromDirs(self,folders):
        DFList = []
        for folder in folders:
            DFList = DFList + [self.getVarsFromDir(folder)]
        DF = pd.concat(DFList)
        return DF    
        
    def getRelVars(self,relVars):
        if not type(relVars) is list: relVars = [relVars]
        DFList = []
        for sweepDir in self.sweepDirs:
            DD = dataDir.DataDir(self.baseDir + sweepDir)
            DF = DD.getScalerVars(relVars,dtype='DF')
            DF['sweepDir'] = sweepDir
            DFList = DFList + [DF]
        DF = pd.concat(DFList)
        DF = DF.set_index('sweepDir')
        return DF
    
    
    
    def getRelSweepDirs(self,relVarsConds, logic='and'):
        
        DF = self.getRelVars(relVarsConds.keys())
        for key,value in relVarsConds.items():
            check = True
            if key == 'le':
                check = DF[key]<=value
            elif key == 'ge':
                pass
            elif key == 'gt':
                pass
            elif key == 'lt':
                pass
            elif key == 'equal':
                pass
        
