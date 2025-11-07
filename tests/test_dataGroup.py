#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  7 16:22:09 2025

@author: marcus
"""

# from dmanage import dfmethods as dfm
from dmanage.group import makeDataGroup 
from dmanage.unit import makeDataUnit  
from dmanage.plugins import vsim

DataDir = makeDataUnit(vsim.loader.VSim)
class MyDataDir(DataDir):
    def __init__(self,dataDir=None):
        super().__init__(dataDir)
        # add personal component loader here that modifies self Obj
        # personalSimulationLoader(dataDir,self)
        
        ####   add any attributes here    ####
        
    #### Add person methods here   ####
SweepDir = makeDataGroup(MyDataDir)
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
    DF = SD.Hists.readAsDF(histName,nc=1)
    print(DF)
    
    histName = 'Vout'
    DF = SD.Hists.readAsDF(histName,nc=2)
    print(DF)
    
    partName = 'electronsT'
    DF = SD.Parts.readAsDF(steps=None,partType=partName,nc=4,ncPass=True)
    print(DF)
    
    SD.PreVars.read('VDC')
    
    
    
    
    
    
    
    
    