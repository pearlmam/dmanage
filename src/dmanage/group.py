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
import functools

from dmanage.decorate import override
#import dmanage.dfmethods as dfm
import dmanage.methods as methods

class PurePython:
    """
    Inheritance class to make DataUnit a pure python class rather than inheriting 
    from `object`, for __bases__ assignment in makeDataUnit(). 
    """
    pass

def make_data_group(base):
    """Makes a DataGroup object with inheritance
    
    Setting the __bases__ attribute is the best way to do this for a number of reasons
    1. The object prints to the terminal with fewer wrapped namespaces
    2. I think this allows the super() function to work better with multiprocess.Pool class
    3. isinstance() works in multiprocess.Pool class
    
    This function will fail if the DataGroup and/or the base input class does not
    inherit from a pure python class. If no inheritance is set, the inheritance defaults
    to an object class. setting the __base__ attribute on a object class with a pure python class
    will throw an error.
    """
    DataGroup.__bases__ = (base,)
    return DataGroup


class DataGroup(PurePython):
    
    """
    opens a sweep data directory containing VSim data directories for common analysis I use. 
    Plotting relevant histories, plotting electrons, sweep data, etc.
    Can generate a data management lookup spreadsheet to visualize the available data directories
    PurePython inheritance is required for inheritance override by make_data_group()
    
    """
    
    def __init__(self, baseDir, unitType='dir', nc=1):
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
        # NEEDS STANDARD NAME FOR ATTRIBUTES, not sweepDir, and deal with baseDir for both Unit and Group???
        # attributes
        
        baseDir = os.path.join(baseDir,'')
        self.baseDir = baseDir
        self.processedDir = 'processed/'
        self.resDir = os.path.join(self.baseDir,self.processedDir)
        self.sweepResDir = os.path.join(self.resDir,'sweep/')
        self.baseNameDepth=3
        # sweep data directories
        #print('Opening %s...'%baseDir, end = ' ')
        #startTime = time.time()
        self.ignoreDirs = [self.processedDir]
        if unitType == 'dir':
            self.dataUnits = self.get_dunits(baseDir, nc=nc)
        else:
            self.dataUnits = self.get_data_files(baseDir)
            
        if len(self.dataUnits) == 0: raise Exception("There are no Data Directories in '%s'" % self.baseDir)
        self.dataUnits = natsort.natsorted(self.dataUnits)
        # open one data directory to load any relevant DataUnit info
        super().__init__(os.path.join(baseDir, self.dataUnits[0]))
        #self.baseDir = os.path.join(baseDir,'')   # overwrite baseDir again,
        
        self._wrap_methods()
 
        #executionTime = time.time()-startTime
        #print('Done in %0.3f Seconds'%executionTime)

    @staticmethod
    def inheritance_level():
        """qualifier to determine the hierarchy level for wrapping methods
        no self input parameter because calling it like below gives error:
        base = self.__class__
        level = base.inheritance_level()

        """
        return 'DG'

    def load(self,dataDir=None,iLevel='DG'):
        # step through inheretanceLevels
        base = self.__class__
        level = base.inheritance_level(self)
        while not (level.lower() == 'dg'):
            if len(base.__bases__) < 1:
                raise Exception("Inheritance chain does not include level '%s'"%level)
            base = base.__bases__[0]
            level = base.inheritance_level(self)
        return base(dataDir)
    
    def _wrap_methods(self):
        """Scan all attributes and wrap methods of component objects and self methods"""
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
            # if method_name.startswith("_"):
            #     continue  # skip private methods?
            if not hasattr(method, "_override"):
                continue  # skip methods without '_override' attribute
            # if method._override == 'default': # ??? Apply the correct wrapper
            wrapped = self._make_wrapper(comp_name or "self", method_name)
            # types.MethodType() includes self in the method call, or something like that
            setattr(target, method_name, types.MethodType(wrapped, target))
            
    def _make_wrapper(self, component_name, method_name):
        """
        Private method which wraps the component method with call to
        on_component_call() hook. also allows access to the original method

        """
        func = get_component_method(self,component_name, method_name)
        @functools.wraps(func)
        def wrapper(_self, *args, **kwargs):
            return self.on_method_call(
                component_name,
                method_name,
                *args,
                **kwargs,
            )
        return wrapper
    
    
    def _on_method_call(self, dataUnit, component_name, method_name, *args, **kwargs):
        """iteration method: loads DU and returns result of the component method
        NOTE: when called from a multiprocess.Pool and MyDataGroup Class is 
            created in another module, the super() function raises an exception
               "TypeError: super(type, obj): obj (instance of MySweepDir) is not an 
               instance or subtype of type (DataGroup)."
            isinstance() does not recognize that self is an instance of DataGroup...
            That's why the super uses its self.__class__.__bases__[0].
            I think I solved this with the improved make_data_group method?
            TO DO: Maybe I need to chain the inheritance better... ie not use the makeDataGroup()
        
        """
        
        # print(self.__class__.__bases__)
        # print(isinstance(self,self.__class__.__bases__))
        # print(isinstance(self,DataGroup))
        du = super().load(os.path.join(self.baseDir,dataUnit),iLevel='DU') 
        # DD = super(self.__class__.__bases__[0],self).load(os.path.join(self.baseDir,sweepDir),iLevel='DU') 
        # DD = self.load(os.path.join(self.baseDir,dataUnit),iLevel='DU') 
        
        du_func = get_component_method(du,component_name, method_name)
        
        # this allows for handling other _override kinds
        orKind = du_func._override
        orLevel = du_func._level
        orArgs = du_func._kwargs
        
        # if orKind == 'plot':  # ??? to do
        #     backEnd = mpl.get_backend()
        #     mpl.use('agg')
        #     # print(mp.current_process())
        #     pid = os.getpid()
        #     kwargs['fig'] = pid

        # elif orKind != 'default':
        #     varOverrideMethod = getattr(component,overrideKind)
        #     varValue = varOverrideMethod()
        #     kwargs[overrideKind] = varValue
        
        return du_func( *args, **kwargs )
    
    def on_method_call(self, component_name, method_name,  *args, **kwargs):
        """parallel iterater method: loads all DDs and returns list of component method results"""
        if 'ncPass' in kwargs:
            ncPass = kwargs.pop('ncPass')
        else:
            ncPass = False
        originalMethod = get_component_method(self,component_name, method_name)
        orKind = originalMethod._override
        orLevel = originalMethod._level
        orArgs = originalMethod._kwargs
        method = methods.wrapper.parallelize_iterator_method(self._on_method_call, ncPass=ncPass)
        results = method(self.dataUnits, component_name, method_name, *args, **kwargs)
        if orKind == 'DataFrame':
            results =pd.concat(results,**orArgs)
        elif orKind == 'dict':
            results = combine_dicts(results)
        return results
    
    def get_data_files(self, baseDir=None):
        if type(baseDir) == type(None):
            baseDir = self.baseDir
        filenames = os.listdir(baseDir)
        sweepDirs = []
        for filename in filenames:
            if self.is_valid(filename): 
                sweepDirs.append(filename)
            else: 
                pass
        return sweepDirs
    
    
    def _get_dunits(self, subDirs, baseDir):
        """looped iterator method: returns list of valid sweep directories"""
        sweepDirs = []
        if type(subDirs) != list: subDirs = [subDirs]
        for subDir in subDirs:
            # print(root)
            skip = False
            for ignoreDir in self.ignoreDirs:
                if ignoreDir in subDir:
                    skip = True
            
            if self.is_valid(subDir) and not skip:
                subDir = os.path.join(subDir,'')  # make sure it ends with '/' so that it knows its a directory.
                sweepDirs.append(subDir.replace(baseDir,''))
            else: 
                pass
        return sweepDirs
       
    def get_dunits(self, baseDir=None, nc=1):
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
        get_dunits_ = methods.wrapper.parallelize_looped_method(self._get_dunits, ncPass=False)
        if type(baseDir) == type(None):
            baseDir = self.baseDir
        subDirs = list(list(zip(*os.walk(baseDir,followlinks=True)))[0])
        sweepDirs = get_dunits_(subDirs,baseDir)

        return sweepDirs
        
    def gen_basename(self, theInput, depth=10):
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
    
    def _get_vars_from_dir(self, folder, dtype='DataFrame', Nrepeat=1, depth=10):
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
    
    def get_vars_from_index(self, mi, dtype='DataFrame'):
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
        
        
    
    
    def get_vars_from_dir(self, folders):
        DFList = []
        for folder in folders:
            DFList = DFList + [self._get_vars_from_dir(folder)]
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
    
    def get_sweep_dirs(self, relVarsConds, logic='and'):
        
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
            
    

def get_component_method(obj,component_name, method_name):
    if component_name == 'self':
        # the "component" is actually self
        component = obj
    else: 
        #The method is within a component
        component = getattr(obj,component_name)
    
    func = getattr(component,method_name)
    return func

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

