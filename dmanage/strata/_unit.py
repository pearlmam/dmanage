#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:09:02 2021
dataUnit stuff
@author: marcus
"""

import os
from pathlib import Path

__all__ = ["make_data_unit","DataUnit"]

def make_data_unit(base=None,name=None):
    """ Creates DataUnit class
    This creates the DataUnit class with the inherited components from the base class
    
    Parameters
    ----------
    base : class
        This is the base class to inherit that consists of the components required for analysis

    Returns
    -------
    class
        This is the DataUnit class with the components.

    """
    ##### mmight need to check for classes with the same name because it might clash???
    if base is None:
        if name is None:
            raise Exception('With no base specified, a name must be given')
        else:
            return type(f"{name}DataUnit", (DataUnit,), {})
    else:
        if name is None:
            name = base.__name__
        return type(f"{name}DataUnit", (DataUnit, base), {})
 
class DataUnit():
    """Inherit from this class to enable dmanage functionality
    """
    def __init__(self,dataPath,*args,**kwargs):
        """Loads components of the DataUnit (folder or file)
        This is the base data unit class which consists of components and arrays inherited from a base class. The base class is unique to each simulation, experiment, or application.

        Parameters
        ----------
        dataPath : str, required
            This is the path to the file or folder
        
        Returns
        -------
        None.

        """
        
        super().__init__(dataPath,*args,**kwargs)   # ??? do I want to have to make a component assembler?
        # define attributes
        self.processedDir = 'processed/'
        self.unitType = (os.path.isdir(dataPath)*'dir' or os.path.isfile(dataPath)*'file'  or
                         Path(dataPath).suffix =='.test' or 'UNDEFINED')
        if self.unitType == 'UNDEFINED':
            raise Exception("Undefined unit: '%s' is neither a directory or a file"%dataPath)
        if  self.inheritance_level() == 'DU':
            # this is so the DataGroup paths don't get overridden when loading DU info.
            self.dataUnit = dataPath
            if self.unitType == 'dir':
                self.baseDir = os.path.join(dataPath,'')
            else:
                self.baseDir = os.path.join(os.path.dirname(dataPath),'')
            self.resDir = self.baseDir+'processed/'
      
    # def is_valid(self,folder):
    #     raise Exception("DataUnit must define 'is_valid()' method to check the validity of the data unit")
        
    @staticmethod
    def inheritance_level():
        return 'DU'