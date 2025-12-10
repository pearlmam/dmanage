# common packages
import pandas as pd
import numpy as np
import os

# necessary packages for data hierarchy
from dmanage.group import make_data_group
from dmanage.unit import make_data_unit
from dmanage.decorate import override

DataUnit = make_data_unit()
class MyDataUnit(DataUnit):
    """this is a simple DataUnit class
    """
    def __init__(self,unitpath):
        """open the data unit
        """
        self.dataUnit = unitpath
        
    def is_valid(self,dataUnit):
        """returns bool if the unit is a valid data unit. 
        
        the DataGroup.__init__() method uses this to check if the file or 
        directory is valid. This method MUST have one input.
        
        Parameters
        ----------
        dataUnit : path to the dataunit
        """
        # enter validity check code here
        return True
    
DataGroup = make_data_group(MyDataUnit)
class MyDataGroup(DataGroup):
    """this is a simple DataGroup class
    """
    def __init__(self,grouppath):
        """open the data group. super().__init__ checks the path for data units
        """
        dataUnitType = 'file'  # options: 'file' or 'dir'
        super().__init__(grouppath,dataUnitType=dataUnitType)

if __name__ == "__main__":
    # unit and group paths
    unitpath = '/path/to/dataUnit'
    grouppath = '/path/to/dataGroup'
    
    # instantiate the data unit for testing unit methods
    DU = MyDataUnit(unitpath)
    
    # instantiate the data group for testing group methods
    DG = MyDataUnit(grouppath)
