#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 24 16:44:38 2025

@author: marcus
"""
import os

from dmanage.unit import make_data_unit
from dmanage.plugins import vsim
from dmanage.server.basic import Server

DataDir = make_data_unit(vsim.loader.VSim)
class MyDataDir(DataDir):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        
        ####   add any attributes here    ####
        
    #### Add person methods here   ####

      
if __name__ == "__main__":
    # for paramiko
    #setup ssh keys for local computer
    # $ ssh-keygen -t rsa
    # $ cat ~/.ssh/id_rsa.pub | ssh 127.0.0.1 'cat >> .ssh/authorized_keys'
    

    ###### server connection info
    homeDir = os.getenv("HOME")
    computer='127.0.0.1'
    server = Server(computer=computer)
    
    ###### vsim pre file inputs
    sourcePreDir = '%s/Documents/SimulationProjects/CFA_L-4953/VSimModels/CFA/'%homeDir
    destPreDir = '%s/Documents/preWorkspace/CFA/'%homeDir
    
    ######  vsim run options
    runBaseLoc = '%s/Documents/CFAdata/'%homeDir
    maxProcs=8
    
    server.connect()
    server.put_dir(sourcePreDir, destPreDir, ['.mac', '.pre'], output=True)
    args = ' --preLoc %s --runBaseLoc %s --maxProcs %s'%(destPreDir, runBaseLoc,maxProcs)
    
    ##### send job submit script and run
    scriptName = 'test_jobSubmit.py'
    workspace = '%s/Documents/pythonWorkspace/'%homeDir
    script = './' + scriptName
    sourceDir = './'
    # ECEsim.putDir(sourceDir,workspace,['.py'],output=True)
    server.put_dir(sourceDir, workspace, ['all'], output=True)
    
    server.run_script(workspace + scriptName, conda='dmanage', args=args)
    server.close() 
    
    

