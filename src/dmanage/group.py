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
import natsort
#import dmanage.dfmethods as dfm
import dmanage.methods as methods

class Dummy: 
    """
    Inheritance class to make DataUnit a pure python class rather than inheriting from `object`, for __bases__ assignment in makeDataUnit()
    """
    pass

def makeDataGroup(Base):
    DataGroup.__bases__ = (Base,)
    return DataGroup
    
    
class DataGroup(Dummy):
    
    """
    opens a sweep data directory containing VSim data directories for common analysis I use. 
    Plotting relevant histories, plotting electrons, sweep data, etc
    Can generate a data managment lookup spreadsheet to visualize the availiable data directories
    
    
    """
    
    def __init__(self,baseDir,nc=1):
        """
        

        Parameters
        ----------
        baseDir : string 
            path to the data directory.
        nc : int, optional
            number of cores to search the directories for valid folders. The default is 1.

        Raises
        ------
        Exception
            DESCRIPTION.

        Returns
        -------
        None.

        """
        
        # sweep data directories
        print('Opening %s...'%baseDir, end = ' ')
        startTime = time.time()
        # initial attributes required by getDDs
        self.processedDir = 'processed'
        self.ignoreDirs = [self.processedDir]
        
        self.sweepDirs = self.getDDs(baseDir,nc=nc)
        if len(self.sweepDirs) == 0: raise Exception("There are no Data Directories in '%s'"%self.baseDir)
        self.sweepDirs = natsort.natsorted(self.sweepDirs)
        super().__init__(os.path.join(baseDir,self.sweepDirs[0]))
        self._wrap_component_methods()
        
        
        # attributes
        self.baseDir = os.path.join(baseDir,'')
        self.resDir = self.baseDir+self.processedDir + '/'
        self.sweepResDir = self.resDir + 'sweep/'
        self.dataLookupFile = self.baseDir + 'dataLookup.xlsx'
        self.baseNameDepth=3
        
        
        executionTime = time.time()-startTime
        print('Done in %0.3f Seconds'%executionTime)
        
    def inheritanceLevel():
        """qualifer to determine the hierarchy level for wrapping methods"""
        return 'DG'
    
    def load(self,dataDir=None,iLevel='DG'):
        # step through inheretanceLevels
        base = self.__class__
        level = base.inheritanceLevel()
        while not (level.lower() == 'dg'):
            if len(base.__bases__) < 1:
                raise Exception("Inheritance chain does not include level '%s'"%level)
            base = base.__bases__[0]
            level = base.inheritanceLevel() 
        return base(dataDir)
    
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
            self._wrap_target_methods(attr_value, comp_name=attr_name)
        self._wrap_target_methods(self, comp_name=None)
        
    def _wrap_target_methods(self,target,comp_name=None):
        # Wrap all public methods of the component
        for method_name, method in inspect.getmembers(target, predicate=inspect.isroutine):
            if method_name.startswith("_"):
                continue  # skip private methods
            elif not hasattr(method, "_override"):  # if you want to use decorators
                continue  # skip methods without '_override' attribute
            # elif not 'read' in method_name:
            #     continue  # skip methods without 'DF' in method name
            original_func = method
            wrapped = self._make_wrapper(comp_name or "self", method_name, original_func)
            # types.MethodType() includes self in the method call, or something like that
            setattr(target, method_name, types.MethodType(wrapped, target))
            #self._original_methods[f"{attr_name}.{method_name}"] = original_func # if you want to crate a dict of all original methods


       
    def _make_wrapper(self, component_name, method_name, original_func):
        """
        Private method which wraps the component method with call to
        on_component_call() hook. also allows access to the original method

        """
        def wrapper(_self, *args, **kwargs):
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
        """iteration method: loads DU and returns result of the component method
        NOTE: when called from a pathos.multiprocessing.Pool and MyDataGroup Class is 
            created in another module, the super() functionraises an exception
               "TypeError: super(type, obj): obj (instance of MySweepDir) is not an 
               instance or subtype of type (DataGroup)."
            isinstance() does not recognize that self is an instance of DataGroup...
            That's why the super uses its self.__class__.__bases__[0].
            TO DO: Maybe I need to chain the inheritance better... ie not use the makeDataGroup()
        
        """
        # print(self.__class__.__bases__)
        # print(isinstance(self,self.__class__.__bases__))
        # print(isinstance(self,DataGroup))
        DD = super().load(os.path.join(self.baseDir,sweepDir),iLevel='DU') 
        # DD = super(self.__class__.__bases__[0],self).load(os.path.join(self.baseDir,sweepDir),iLevel='DU') 
        # DD = self.load(os.path.join(self.baseDir,sweepDir),iLevel='DU') 
        if component_name == 'self':
            # the "component" is actually self
            component = DD
        else: 
            #The method is within a component
            component = getattr(DD,component_name)
        
        DD_func = getattr(component,method_name)
        return DD_func( *args, **kwargs )
    
    def on_component_call(self, component_name, method_name, original, *args, **kwargs):
        """parallel iterater method: loads all DDs and returns list of component method results"""
        if 'ncPass' in kwargs:
            ncPass = kwargs.pop('ncPass')
        else:
            ncPass = False
        method = methods.wrapper.parallelize_iterator_method(self._on_component_call,ncPass=ncPass ) 
        DFs = method(self.sweepDirs,component_name, method_name, original, *args, **kwargs)
        #self._wrap_component_methods()                # rewrap component methods with SD equivalent
        return DFs
    

    def _getDDs(self,subDirs,baseDir):
        """looped iterator method: returns list of valid sweep directories"""
        sweepDirs = []
        if type(subDirs) != list: subDirs = [subDirs]
        for subDir in subDirs:
            # print(root)
            skip = False
            for ignoreDir in self.ignoreDirs:
                if ignoreDir in subDir:
                    skip = True
            
            if self.isValid(subDir) and not skip: 
                sweepDirs.append(subDir.replace(baseDir,''))
            else: 
                pass
        return sweepDirs
       
    def getDDs(self,baseDir=None,nc=1):
        """
        parallel iterator method: returns list of valid sweep directories

        Parameters
        ----------
        baseDir : TYPE, optional
            DESCRIPTION. The default is None.
        nc : TYPE, optional
            DESCRIPTION. The default is 1.

        Returns
        -------
        sweepDirs : TYPE
            DESCRIPTION.

        """
        _getDDs = methods.wrapper.parallelize_looped_method(self._getDDs,ncPass=False)
        if type(baseDir) == type(None):
            baseDir = self.baseDir
        subDirs = list(list(zip(*os.walk(baseDir,followlinks=True)))[0])
        sweepDirs = _getDDs(subDirs,baseDir)

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
        
    # def getRelVars(self,relVars):
    #     if not type(relVars) is list: relVars = [relVars]
    #     DFList = []
    #     for sweepDir in self.sweepDirs:
    #         DD = DataDir(self.baseDir + sweepDir)
    #         DF = DD.getScalerVars(relVars,dtype='DF')
    #         DF['sweepDir'] = sweepDir
    #         DFList = DFList + [DF]
    #     DF = pd.concat(DFList)
    #     DF = DF.set_index('sweepDir')
    #     return DF
    
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
            
    