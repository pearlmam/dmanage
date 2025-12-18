#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:09:02 2021
dataUnit stuff
@author: marcus
"""
import io
import pandas as pd
import os

import sys
import inspect

class PurePython:
    """
    Inheritance class to make DataUnit a pure python class, for __bases__ assignment in makeDataUnit()
    """
    pass

def make_data_unit(base=PurePython):
    """ Creates DataUnit class
    This creates the DataUnit class with the inherited components from the base class
    The base class must be a pure python class because DataUnit inherits from PurePython and overwriting 
    __bases__ might throw an error: "TypeError: __bases__ assignment: 'A' deallocator differs from 'object'"
    If DataUnit did not inherit from this dummy PurePython, it default inherits from `object` and __bases__ cant be overwritten 
    with my python class. Some might be true if your class is not a pure python class.
    Parameters
    ----------
    base : class
        This is the base class to inherit that consists of the components required for analysis

    Returns
    -------
    class
        This is the DataUnit class with the components.

    """
    DataUnit.__bases__ = (base,)
    return DataUnit
    
class DataUnit(PurePython):
    
    def __init__(self,dataPath):
        """Loads components of the DataUnit (folder or file)
        This is the base data unit class which consists of components and methods inherited from a base class. The base class is unique to each simulation, experiment, or application.

        Parameters
        ----------
        dataPath : str, required
            This is the path to the file or folder
        computer : str, optional
            UNIMPLEMENTED! The ip address or name of the computer where the dataUnit is. The default is 'local'.
        user : str, optional
            The username credentials for the login if needed. Set up an ssh public and private keys to log in to the server, no password option is given here. The default is None.

        Returns
        -------
        None.

        """
        super().__init__(dataPath)   # ??? do I want to have to make a component assembler?
        # define attributes
        self.dataUnit = dataPath
        self.unitType = os.path.isdir(dataPath)*'dir' or os.path.isfile(dataPath)*'file' or 'UNDEFINED'
        if self.unitType == 'UNDEFINED':
            raise Exception("Undefined unit: '%s' is neither a directory or a file"%dataPath)
        if self.unitType == 'dir':
            self.baseDir = os.path.join(dataPath,'')
        else:
            self.baseDir = os.path.join(os.path.dirname(dataPath),'')
        self.resDir = self.baseDir+'processed/'
        
    def inheritance_level(self):
        return 'DU'
    
    def load(self,dataPath=None,iLevel='DU'):
        # step through inheritance levels
        base = self.__class__
        level = base.inheritance_level(self)
        while not (level.lower() == 'du'):
            if len(base.__bases__) < 1:
                raise Exception("Inheritance chain does not include level '%s'"%level)
            base = base.__bases__[0]
            level = base.inheritance_level(self)
        return base(dataPath)
    

