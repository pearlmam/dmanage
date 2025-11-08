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
    
    
    ##### setup optimization
    model = om.Group()
    model.add_subsystem('cfa', CFA(folder), promotes_inputs=['iVDC'])
    
    model.set_input_defaults('iVDC', 5)

    prob = om.Problem(model)
    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options['optimizer'] = 'SLSQP'
    
    prob.model.add_design_var('iVDC', lower=0, upper=len(VDCs))
    prob.model.add_objective('cfa.Pout',scaler=-1.0)
    # prob.model.add_constraint('cfa.noise', lower=-35)
    
    prob.setup()
    
    # prob.set_val('cfa.folder', folder)
    # prob.set_val('cfa.VDC', VDCs)
    prob.driver.options['debug_print'] = ['desvars']
    prob.run_driver()
    print(prob.get_val('cfa.Pout'))
