#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  7 16:22:09 2025

@author: marcus
"""

# from dmanage import dfmethods as dfm
from dmanage.group import make_data_group
from dmanage.unit import make_data_unit
from dmanage.plugins import vsim
from dmanage.decorate import override

DataDir = make_data_unit(vsim.loader.VSim)
class MyDataDir(DataDir):
    def __init__(self,dataDir=None):
        super().__init__(dataDir)
        # add personal component loader here that modifies self Obj
        # personalSimulationLoader(dataDir,self)
        
    @override()
    def get_scalars(self, names):
        return self.PreVars.read(names)
    ####   add any attributes here    ####
        
    #### Add person methods here   ####
SweepDir = make_data_group(MyDataDir)
class MySweepDir(SweepDir):
    # def __init__(self,dataDir=None):
    #     #super().__init__(dataDir
    #     pass
    pass

if __name__ == "__main__":
    folder = './test_data/vsim_data/VDC-87.8e3/'
    DD = MyDataDir(folder)
    
    folder = './test_data/vsim_data/'
    SD = MySweepDir(folder)
    
    histName = 'Pout'
    DF = SD.Hists.read_as_df(histName, nc=1)
    print(DF)
    
    histName = 'Vout'
    DF = SD.Hists.read_as_df(histName, nc=2)
    print(DF)
    
    partName = 'electronsT'
    DF = SD.Parts.read_as_df(steps=None, partType=partName, nc=4, ncPass=True)
    print(DF)
    
    SD.PreVars.read('VDC')
    
    scalars = SD.get_scalars('VDC')
    
    
    
    
    
    
    