#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan  1 10:00:44 2026

@author: marcus
"""
import dmanage.remote.rpc_old as rpc
import Pyro5.api
import Pyro5.server
import inspect

from project import MyDataUnit

if __name__ == "__main__":


    dataPath = '/home***REMOVED***Documents/SimulationProjects/dmanage/tests/test_data/vsim_data/VDC-87.8e3/'
    module = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/pythonProject/core/dataDir'
    obj = 'MyDataDir'
    
    Peer = rpc.LocalPeer()
    Peer.NameServer.start(subProc=True)
    Peer.PyroObject.create_object(obj,module=module,dataPath=dataPath)
    Peer.PyroObject.start(subProc=True)
    
    DD = Peer.Client.get_remote_object(name='Obj')
    
    # Peer.stop()
    
    
    