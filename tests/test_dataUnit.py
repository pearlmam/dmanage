#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 14 13:31:59 2025

@author: marcus
"""

from dmanage.dataUnit import makeDataUnit
from dmanage.components.vsim import vsim

DataDir = makeDataUnit(vsim.VSim)
class MyDataDir(DataDir):
    def __init__(self,dataDir=None):
        super().__init__(dataDir)
        
        ####   add any attributes here    ####
        
    #### Add person methods here   ####


        
if __name__ == "__main__":
    folder = './test_data/vsim_data/VDC-87.8e3/'
    DD = MyDataDir(folder)
    
    
    ##############################################################
    ## checking the structure of the class
    ##############################################################

    print('Checking types: Histories:\n')
    print(DD.Hists.types)

    print('\nChecking types: Particles:\n')
    print(DD.Parts.types)

    print('\nChecking types: Fields:\n')
    print(DD.Fields.types)

    print('\nChecking types: Geometries:\n')
    print(DD.Geos.files)

    ##############################################################
    ## check data loading
    ##############################################################
    print('\nRead 1D History')
    histName = 'Pout'
    df = DD.Hists.readAsDF(histName)
    print(df)

    print('\nRead 1D Historys')
    histNames = ['Pout','Vout']
    df = DD.Hists.readAsDF(histNames,concat=False)
    print(df)

    print('\nRead 2D Vector History')
    histName = 'EedgeCircleR200'
    df = DD.Hists.readAsDF(histName)
    print(df)

    print('\nRead All particles')
    partType = 'electronsT'
    df = DD.Parts.readAsDF('all',partType=partType,nc=4)
    print(df)

    print('\nRead All Fields')
    fieldName = 'E'
    df = DD.Fields.readAllAsDF(fieldName,nc=4)
    print(df)

    ##############################################################
    ## input deck reading
    ##############################################################
    print('\nRead Pre Variables')
    varNames = ['VDC', 'BSTATIC','PRF_AVG','undefinedVariable']
    out = DD.PreVars.read(varNames,warn=True)
    print(out)