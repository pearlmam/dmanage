# -*- coding: utf-8 -*-
import numpy as np
import openmdao.api as om
import pandas as pd

from test_mdao_run import DataDir,SweepDir,MyDataDir,MySweepDir,CFA2
from dmanage.dfmethods.plot import Plot

if __name__ == "__main__":
    plot = Plot()
    folder = '/media***REMOVED***FASTER/CFAdata/2023/vbSweep/NXY-109/TEND-300e-9/FREQ-1.315e9/iCathode-1000/BSTATIC-0.140/PRF_AVG-450e3/VDC-90.5e3/'
    DD = MyDataDir(folder)
    #### test functions
    
    Pout = DD.getPower()
    noise = DD.getNoiseLevel()
    
    folder = folder + '../'
    SD = MySweepDir(folder)
    
    Pouts = SD.getScalarVars('Pout',nc=8)
    Pouts = np.array([Pout['Pout'] for Pout in Pouts])
    ##### get availiable VDC values for constraints
    VDCs = SD.PreVars.read('VDC',nc=8)
    VDCs = np.array([VDC['VDC'] for VDC in VDCs])
    
    
    ##### setup optimization
    model = om.Group()
    model.add_subsystem('cfa', CFA2(folder), promotes_inputs=['VDC'])
    
    model.set_input_defaults('VDC', VDCs[6])

    prob = om.Problem(model)
    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options['optimizer'] = 'SLSQP'
    
    prob.model.add_design_var('VDC', lower=VDCs[0], upper=VDCs[-1])
    prob.model.add_objective('cfa.Pout',scaler=-1.0)
    # prob.model.add_constraint('cfa.noise', lower=-35)
    
    prob.setup()
    
    # prob.set_val('cfa.folder', folder)
    # prob.set_val('cfa.VDC', VDCs)
    prob.driver.options['debug_print'] = ['desvars']
    # prob.check_partials()
    prob.run_driver()
    
    
    print(prob.get_val('cfa.Pout'))

    DF = pd.DataFrame(np.vstack([VDCs,Pouts]).T,columns=['VDC','Pout'])
    DF = DF.set_index('VDC')
    fig,ax = plot.plot1d(DF)
    
    
    gradCheck = (Pouts[6]-Pouts[5])/(VDCs[6]-VDCs[5])
