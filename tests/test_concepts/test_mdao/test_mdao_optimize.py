# -*- coding: utf-8 -*-
import numpy as np
import openmdao.api as om

from test_mdao_run import DataDir,SweepDir,MyDataDir,MySweepDir,CFA


if __name__ == "__main__":
    
    folder = '/media***REMOVED***FASTER/CFAdata/2023/vbSweep/NXY-109/TEND-300e-9/FREQ-1.315e9/iCathode-1000/BSTATIC-0.140/PRF_AVG-450e3/VDC-90.5e3/'
    DD = MyDataDir(folder)
    #### test functions
    
    Pout = DD.getPower()
    noise = DD.getNoiseLevel()
    
    folder = folder + '../'
    SD = MySweepDir(folder)
    
    
    ##### get availiable VDC values for constraints
    VDCs = SD.PreVars.read('VDC',nc=8)
    VDCs = np.array([VDC['VDC'] for VDC in VDCs])
    
    # model = om.Group()
    # model.add_subsystem('cfa', CFA(folder))

    # prob = om.Problem(model)
    # prob.setup()
    
    # # prob.set_val('cfa.folder', folder)
    # prob.set_val('cfa.VDC', VDCs[0])
    
    # prob.run_model()
    # print(prob['cfa.Pout'])
    
