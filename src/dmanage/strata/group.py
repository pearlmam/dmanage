#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:14:34 2021
SweepDir
@author: marcus
"""

import os
import inspect
import pandas as pd
import natsort
import functools
import matplotlib as mpl

from pathlib import Path

import dmanage.utils.objinfo as objinfo
import dmanage.utils.combine as combine
from dmanage.parallel import parallelize_iterator_method, parallelize_looped_method

from dmanage.strata import helpers


__all__ = ["make_data_group"]
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
    
    def __init__(self, baseDir, unitType='dir', nc=1,testN=100,*args,**kwargs):
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
        if unitType == 'test':
            self.dataUnits = ['file-%02.d.test'%value for value in range(0,testN)]
        elif unitType in ['dir','file']:
            self.dataUnits = self.get_dunits(baseDir,unitType=unitType)
        else:
            raise Exception('Invalid unitType')
        
            
        if len(self.dataUnits) == 0: raise Exception("There are no Data Directories in '%s'" % self.baseDir)
        self.dataUnits = natsort.natsorted(self.dataUnits)
        # open one data directory to load any relevant DataUnit info
        super().__init__(os.path.join(baseDir, self.dataUnits[0]),*args,**kwargs)
        #self.baseDir = os.path.join(baseDir,'')   # overwrite baseDir again,
        
        self._wrap_methods()
 
        #executionTime = time.time()-startTime
        #print('Done in %0.3f Seconds'%executionTime)

    @staticmethod
    def inheritance_level():
        """qualifier to determine the hierarchy level for wrapping arrays
        no self input parameter because calling it like below gives error:
        base = self.__class__
        level = base.inheritance_level()

        """
        return 'DG'

    def _wrap_methods(self):
        """Scan all attributes and wrap arrays of component objects and self arrays"""
        for attr_name, attr_value in vars(self).items():
            if attr_name.startswith("_"):
                continue  # skip internal attributes
            # Detect component-like objects (skip classes, numbers, etc.)
            if inspect.isclass(attr_value) or objinfo.is_literal(attr_value) or objinfo.is_pandas(attr_value):
                continue
            self._wrap_target_methods(attr_value, comp_name=attr_name)
        self._wrap_target_methods(self, comp_name=None)
        
    def _wrap_target_methods(self,target,comp_name=None):
        # Wrap all public arrays of the component
        for method_name, method in inspect.getmembers(target, predicate=inspect.isroutine):
            # if method_name.startswith("_"):
            #     continue  # skip private arrays?
            if not hasattr(method, "_override"):
                continue  # skip arrays without '_override' attribute
            # if method._override == 'default': # ??? Apply the correct wrapper
            wrapped = make_wrapper(self,comp_name or "self", method_name)
            
            # types.MethodType() includes self in the method call, or something like that
            setattr(target, method_name, wrapped)
    
    def get_DataUnit(self,dataUnit=0,args=(),kwargs={}):
        base = get_base(self,iLevel='du')
        if isinstance(dataUnit,int):
            dataUnit = Path(os.path.join(self.baseDir,self.dataUnits[dataUnit]))
        elif isinstance(dataUnit,(str,Path)):
            dataUnit = Path(dataUnit)
        else:
            raise TypeError("'dataUnit' must be int or path-like.")
        
        if Path(self.baseDir) not in dataUnit.parents:
            dataUnit = os.path.join(self.baseDir,dataUnit)
        
        uriKey = str(dataUnit)
        uriKey = uriKey.replace(self.baseDir,'')
        
        du = base(dataUnit,*args,**kwargs)
        
        # check if proxy and Pyroize
        if hasattr(self,'_pyroDaemon'): 
            uri = self._create_pyro_uri(du,uriKey)
            # proxy = self._create_pyro_proxy(du)
            return uri
        else:
            return du
        
    
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
    

    def _get_dunits(self, candidates, baseDir, unitType):
        """
        Processor: Filters candidates based on validity and ignore lists.
        """
        valid_units = []
        base_path = Path(baseDir)
    
        for item in candidates:
            item_path = Path(item)
            
            # 1. Skip if any part of the path is in ignoreDirs
            if any(part in self.ignoreDirs for part in item_path.parts):
                continue
    
            # 2. Run your application-specific validation
            if self.is_valid(item):
                try:
                    # Calculate relative path reliably
                    rel_path = item_path.relative_to(base_path)
                    
                    # Format directories with trailing slash if requested
                    if unitType == 'dir':
                        output = str(rel_path) + os.sep
                    else:
                        output = str(rel_path)
                    
                    valid_units.append(output)
                except ValueError:
                    # Handle cases where item is not under baseDir
                    continue
                    
        return valid_units
    
    def get_dunits(self, baseDir=None, unitType='dir', nc=1):
        """
        Orchestrator: Gathers candidates and triggers parallel processing.
        """
        if baseDir is None:
            baseDir = self.baseDir
        
        # Prepare the parallel wrapper
        get_dunits_wrapper = parallelize_looped_method(self._get_dunits, ncPass=False)
    
        candidates = []
        
        # Efficiently collect only what is needed based on unitType
        for root, dirs, files in os.walk(baseDir, followlinks=True):
            if unitType == 'dir':
                candidates.append(root)
            elif unitType == 'file':
                for f in files:
                    candidates.append(os.path.join(root, f))
            else:
                # Handle 'both' or custom logic if needed
                candidates.append(root)
                for f in files:
                    candidates.append(os.path.join(root, f))
    
        # Chunk the candidates and process in parallel
        return get_dunits_wrapper(candidates, baseDir, unitType,nc=nc)
    
    
    # def _get_dunits(self, subDirs, baseDir,unitType):
    #     """looped iterator method: returns list of valid sweep units"""
    #     sweepDirs = []
    #     if type(subDirs) != list: subDirs = [subDirs]
    #     for subDir in subDirs:
    #         # print(root)
    #         skip = False
    #         for ignoreDir in self.ignoreDirs:
    #             if Path(ignoreDir).name in Path(subDir).parts:
    #                 skip = True
            
    #         if self.is_valid(subDir) and not skip:
    #             subDir = os.path.join(subDir,'')  # make sure it ends with '/' so that it knows its a directory.
    #             sweepDirs.append(subDir.replace(baseDir,''))
    #         else: 
    #             pass
    #     return sweepDirs
       
    # def get_dunits(self, baseDir=None, unitType='dir', nc=1):
    #     """
    #     parallel iterator method: returns list of valid sweep directories

    #     Parameters
    #     ----------
    #     baseDir : TYPE, optional
    #         DESCRIPTION. The default is None.
    #     nc : TYPE, optional
    #         DESCRIPTION. The default is 1.

    #     Returns
    #     -------
    #     sweepDirs : TYPE
    #         DESCRIPTION.

    #     """
    #     get_dunits_ = parallelize_looped_method(self._get_dunits, ncPass=False)
    #     if type(baseDir) == type(None):
    #         baseDir = self.baseDir
    #     subDirs = list(list(zip(*os.walk(baseDir,followlinks=True)))[0])
    #     sweepDirs = get_dunits_(subDirs,baseDir,unitType)

    #     return sweepDirs
        
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
            
    # this is here mainly for testing?? The user may want to pickle dataGroups, but for strata testing we dont? 
    def __getstate__(self):
        raise RuntimeError("""Datagroup should not be pickled. Parallelism should only pickle DataUnit""")
            
######################
##   Wrapper funcs
######################

class make_wrapper:
    def __init__(self, instance,component_name, method_name):
        """
        Private method which wraps the component method with call to
        on_component_call() hook. also allows access to the original method
        """
        #### copy func characteristics to wrapper
        func = get_component_method(instance,component_name, method_name)
        functools.update_wrapper(self, func)
        del self.__wrapped__   # delete actual function to have zero connection to DataGroup. no pickling groups!!!
        
        #### add the correct sig to this method
        # sig = inspect.signature(func)  
        sig = helpers.enable_override(func,instance)
        self.originalSig = sig       # original signature used with method call, useful for override kind hook
            
        new_param = inspect.Parameter('dataUnit', inspect.Parameter.POSITIONAL_OR_KEYWORD)
        new_params = [new_param] + list(sig.parameters.values())
        new_sig = sig.replace(parameters=new_params)
        self.__signature__ = new_sig # allows signature to be called on self and return proper inputs
        
        
        
        #### setup parameters
        self.dataUnits = [os.path.join(instance.baseDir,dataUnit) for dataUnit in instance.dataUnits]
        self.base = get_base(instance,iLevel='du')
        self.component_name = component_name
        self.method_name = method_name
        self.orKind = getattr(func,'_override',None)
        self.orLevel = getattr(func,'_level',None)
        self.orArgs = getattr(func,'_kwArgs',None)
    
    # @functools.wraps(self.func)
    def _on_method_call(self,dataUnit, *args, **kwargs):
        """iteration method: loads DU and returns result of the component method
        NOTE: when called from a multiprocess.Pool and MyDataGroup Class is 
            created in another module, the super() function raises an exception
               "TypeError: super(type, obj): obj (instance of MySweepDir) is not an 
               instance or subtype of type (DataGroup)."
            isinstance() does not recognize that self is an instance of DataGroup...
            That's why the super uses its self.__class__.__bases__[0].
            I think I solved this with the improved make_data_group method?
            TO DO: Maybe I need to chain the inheritance better... ie not use the makeDataGroup()
        
        Do NOT want to pass self to this, just base class (DataUnit)
        """
        
        bound = self.originalSig.bind(*args, **kwargs)
        du = self.base(dataUnit) 
        # DD = super(self.__class__.__bases__[0],self).load(os.path.join(self.baseDir,sweepDir),iLevel='DU') 
        # DD = self.load(os.path.join(self.baseDir,dataUnit),iLevel='DU') 
        #print('loading DataUnit Method: %s.%s'%(self.component_name, self.method_name))
        du_func = get_component_method(du,self.component_name, self.method_name)

        if 'plot' in self.orKind.lower():
            pid = os.getpid()
            # print(pid)
            bound.arguments['fig'] = pid
            # kwargs['fig'] = pid
    
        # elif orKind != 'default':
        #     varOverrideMethod = getattr(component,overrideKind)
        #     varValue = varOverrideMethod()
        #     kwargs[overrideKind] = varValue
        
        # result = du_func( *args, **kwargs )
        result = du_func( *bound.args, **bound.kwargs )
        
        

        return result
    
    def __call__(self,  *args, **kwargs):
        """parallel iterater method: loads all DDs and returns list of component method results"""
        if 'ncPass' in kwargs:
            ncPass = kwargs.pop('ncPass')
        else:
            ncPass = False
            
        #### deal with override kinds before
        if 'plot' in self.orKind.lower():  
            backend = mpl.get_backend()
            mpl.use('agg')
            
        ## binding to self, which has original signature plus the dataunit, see self.__signature__
        method = parallelize_iterator_method(self._on_method_call, ncPass=ncPass, bind_func=self)
        results = method(self.dataUnits, *args, **kwargs)
        
        #### deal with override kinds after
        if self.orKind == 'DataFrame':
            results = pd.concat(results,**self.orArgs)
        elif self.orKind == 'dict':
            results = combine.combine_dicts(results)
        if 'plot' in self.orKind.lower():  
            mpl.use(backend)
        return results
    
    
    
    
###########################
##     Helper funcs
#############################

def get_base(instance,iLevel='du'):
    #super(instance,instance).__init__()
    
    # step through inheretanceLevels
    base = instance.__class__
    level = base.inheritance_level()
    while not (level.lower() == iLevel.lower()):
        if len(base.__bases__) < 1:
            raise Exception("Inheritance chain does not include level '%s'"%level)
        base = base.__bases__[0]
        level = base.inheritance_level()
    return base

def get_component_method(obj,component_name, method_name):
    if component_name == 'self':
        # the "component" is actually self
        component = obj
    else: 
        #The method is within a component
        component = getattr(obj,component_name)
    
    func = getattr(component,method_name)
    return func


        

    
    
    
    

