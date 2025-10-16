#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:14:34 2021
SweepDir
@author: marcus
"""
import inspect, types
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
    
    def __init__(self,baseDir):
        # sweep data directories
        print('Opening %s...'%baseDir, end = ' ')
        startTime = time.time()
        self.baseDir = os.path.join(baseDir,'')
        self.sweepDirs = self.getDDs(baseDir,nc=1)
        if len(self.sweepDirs) == 0: raise Exception("There are no Data Directories in '%s'"%self.baseDir)
        self.sweepDirs = natsort.natsorted(self.sweepDirs)
        super().__init__(os.path.join(baseDir,self.sweepDirs[0]))
        self._wrap_component_methods()
        
        
        # attributes
        self.resDir = self.baseDir+'processed/'
        self.sweepResDir = self.resDir + 'sweep/'
        self.dataLookupFile = self.baseDir + 'dataLookup.xlsx'
        self.baseNameDepth=3

        
        executionTime = time.time()-startTime
        print('Done in %0.3f Seconds'%executionTime)

    def _wrap_component_methods(self):
        """Scan all attributes and wrap methods of component-like objects."""
        for attr_name, attr_value in vars(self).items():
            if attr_name.startswith("_"):
                continue  # skip internal attributes
            if not hasattr(attr_value, "__class__"):
                continue  # skip primitives

            # Detect component-like objects (skip classes, numbers, etc.)
            if inspect.isclass(attr_value) or isinstance(attr_value, (int, float, str, dict, list, tuple)):
                continue

            # Wrap all public methods of the component
            for method_name, method in inspect.getmembers(attr_value, predicate=inspect.isroutine):
                if method_name.startswith("_"):
                    continue  # skip private methods
                # elif not hasattr(method, "_component_override"):  # if you want to use decorators
                #     continue  # skip methods without '_component_override' attribute
                elif not 'DF' in method_name:
                    continue
                original_func = method
                wrapped = self._make_wrapper(attr_name, method_name, original_func)
                setattr(attr_value, method_name, types.MethodType(wrapped, attr_value))
                #self._original_methods[f"{attr_name}.{method_name}"] = original_func

    def _make_wrapper(self, component_name, method_name, original_func):
        def wrapper(_self, *args, **kwargs):
            # If subclass defines on_component_call, use it
            if hasattr(self, "on_component_call"):
                return self.on_component_call(
                    component_name,
                    method_name,
                    lambda *a, **kw: original_func(*a, **kw),
                    *args,
                    **kwargs,
                )
            else:
                return original_func(*args, **kwargs)
        return wrapper
    
    def _on_component_call(self, sweepDir,component_name, method_name, original, *args, **kwargs):
        super().__init__(os.path.join(self.baseDir,sweepDir))  
        component = getattr(self,component_name)
        DD_func = getattr(component,method_name)
        return DD_func( *args, **kwargs )
    
    def on_component_call(self, component_name, method_name, original, *args, **kwargs):
        DFs = []
        for sweepDir in self.sweepDirs:
            # this overwrites the component methods with the DD equivalent
            super().__init__(os.path.join(self.baseDir,sweepDir))  
            component = getattr(self,component_name)
            DD_func = getattr(component,method_name)
            DFs = DFs + [DD_func( *args, **kwargs )]
        #DFs = pd.concat(DFs)
        self._wrap_component_methods()                # rewrap component methods with SD equivalent
        return DFs
    
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
            DD = DataDir(self.baseDir + sweepDir)
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
        
