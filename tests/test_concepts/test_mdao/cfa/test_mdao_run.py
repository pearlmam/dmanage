# -*- coding: utf-8 -*-

import copy
import numpy as np
import pandas as pd
import os
import openmdao.api as om
from dmanage.plugins import vsim
from dmanage.unit import make_data_unit
from dmanage.group import make_data_group
import dmanage.dfmethods as dfm
from dmanage.utils.utils import child_override

DataDir = make_data_unit(vsim.loader.VSim)
class MyDataDir(DataDir):
    def __init__(self,dataDir=None):
        super().__init__(dataDir)
        self.tStart = self.getStartup('Pout')
        self.freq = self.PreVars.read('FREQ')['FREQ']
        
    def getStartup(self,histName):
        DF = self.Hists.read_as_df(histName)
        tBuff = 10e-9
        tStart = dfm.signal.get_startup(DF, debug=False) + tBuff
        tend = self.Hists.tend
        if tStart>tend*0.9:
            tStart = tend*0.9
        return tStart

    def getPower(self,histName = 'Pout'):
        DF = self.Hists.read_as_df(histName)
        DF = DF.iloc[DF.index.get_level_values(0)>self.tStart]
        DF = DF.mean().tolist()[0]
        return DF

    def getNoiseLevel(self,histName='Vout'):
        if self.Hists.check_dataset(histName, output=True)[0]:
            maxFreq = 4.2e9
            maxPks=15
            DF = self.Hists.read_as_df(histName, concat=True)
            DF = DF.iloc[DF.index.get_level_values('t')>self.tStart]
            DF = dfm.fft.fft(DF)
            
            DF = DF.iloc[DF.index.get_level_values(0)<maxFreq].sort_index()
            DFA = dfm.fft.fft_amplitude(DF)
            DFP = dfm.fft.fft_phase(DF)
            DFA = 20*np.log10(DFA)
            minFreqDistance = 50e6
            dFreq = DF.index.get_level_values(0)[1]-DF.index.get_level_values(0)[0]
            peakDist = round(minFreqDistance/dFreq)
            
            
            DFpks,props = dfm.signal.find_pks(DFA[DFA.columns[0]], maxPks=maxPks, pRatio=0.08, tRatio=None, height=-50, wlen=None, distance=peakDist, width=None)
            DFpks = pd.concat([DFpks,(DFP.loc[DFpks.index]).reset_index(level=[])],axis=1)
        cutoff=[0,2.5e9]    
        noisePks = DFpks.iloc[DFpks.index<(1.9*self.freq)][DFpks.columns[0]]
        if len(noisePks) > 1:
            twoPks = noisePks.nlargest(2)
            noiseLevel = twoPks.iloc[1]
        else:
            noiseLevel = -np.inf
            sideband = np.nan
        return float(noiseLevel)
    @child_override
    def getScalarVars(self,varList,theRange=[0.75, 1.0],dtype='Dict'):
        """
        determines if varRead is a history or a input variable in vars.py and reads the variable accordingly
        """
        if type(varList) is not list:
            varList = [varList]
        
        dictOrder = copy.deepcopy(varList)
        varList_copy = copy.deepcopy(varList)
        ####### check if varList element is in histories 
        histList = []
        i = 0
        for var in varList:
            if var in self.Hists.types:
                histList.append(var)
                varList_copy.pop(i)
                i-=1
            i+=1
            
        ##### get the values
        varDict = self.PreVars.read(varList_copy) 
        DF = self.Hists.read_as_df(histList, concat=True)
        if not DF.empty: 
            DF = dfm.helper.reduce(DF,'t',method='mean',theRange=theRange)
            varDict.update(DF.to_dict())
            
        #### reorder the dictionary
        dictOrder_copy = copy.deepcopy(dictOrder)
        for var in dictOrder_copy:
            if not var in varDict.keys():
                dictOrder.remove(var)
        varDict = {k: varDict[k] for k in dictOrder}
        
        ##### convert to output format
        if dtype == 'DF':
            varDict = pd.DataFrame(varDict,index=[0])
        elif dtype == 'list':
            varDict = [list(varDict.keys()),list(varDict.values())]
        
        return varDict


SweepDir = make_data_group(MyDataDir)
class MySweepDir(SweepDir):
    def __init__(self,baseDir):
        super().__init__(baseDir)



class CFA1(om.ExplicitComponent):
    """
    optimizes power with voltage constrained by noise level
    """
    def __init__(self,sweepDir):
        super().__init__()
        self.folder=sweepDir
        
    def setup(self):
        self.add_input('VDCs', val=np.ones(16))
        self.add_discrete_input('iVDC', val=0)
        self.add_output('VDC',val=90500.)
        self.add_output('Pout', val=7170204.366679185)
        self.add_output('noise', val=-31.552592955305645)
        #self.output_file = 'CFA_History.h5'
        #self.options['external_output_files'] = [self.output_file]
    
    def setup_partials(self):
        # Finite difference all partials.
        # self.declare_partials('Pout', 'VDC', method='fd')
        self.declare_partials('Pout', 'VDC', method='fd')

    def compute(self,inputs,outputs,discrete_inputs,discrete_outputs):
        """
        
        """
        iVDC = discrete_inputs['iVDC']
        VDCs = inputs['VDCs']
        VDC = float(VDCs[iVDC])
        
        DD = MyDataDir(os.path.join(self.folder,'VDC-%.1fe3'%(VDC/1e3)))
        outputs['Pout'] = DD.getPower()
        outputs['noise'] = DD.getNoiseLevel()
        outputs['VDC'] = VDC


class CFA2(om.ExplicitComponent):
    """
    optimizes power with voltage constrained by noise level
    """
    def __init__(self,sweepDir):
        super().__init__()
        self.folder=sweepDir
        
    def setup(self):

        self.add_input('VDC',val=91800.)
        self.add_output('Pout', val=-8153265.397347919)
        self.add_output('noise', val=-31.552592955305645)
        #self.output_file = 'CFA_History.h5'
        #self.options['external_output_files'] = [self.output_file]
    
    def setup_partials(self):
        # Finite difference all partials.
        # self.declare_partials('Pout', 'VDC', method='fd')
        self.declare_partials('Pout', 'VDC', method='fd',step=0.25e3)

    def compute(self,inputs,outputs):
        """
        
        """
       
        VDC = inputs['VDC']
        # round to the nearest 0.25
        VDC = np.round(VDC/1e3*4)/4*1e3
        DD = MyDataDir(os.path.join(self.folder,'VDC-%.1fe3'%(VDC/1e3)))
        outputs['Pout'] = DD.getPower()
        outputs['noise'] = DD.getNoiseLevel()



if __name__ == "__main__":
    # I need to use previously generated data to test if openMDAO can find the max power, constrained by noise
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
    
    
    model = om.Group()
    model.add_subsystem('cfa', CFA2(folder))
    

    prob = om.Problem(model)
    prob.setup()
    
    # prob.set_val('cfa.folder', folder)
    prob.set_val('cfa.VDC', VDCs[5])

    
    prob.run_model()
    print(prob['cfa.Pout'])
    
    
    
    
    
    
    
    
    # model = om.Group()
    # model.add_subsystem('cfa', CFA())

    # prob = om.Problem(model)
    # prob.setup()

    # prob.set_val('parab_comp.x', 3.0)
    # prob.set_val('parab_comp.y', -4.0)

    # prob.run_model()
    # print(prob['parab_comp.f_xy'])

    # prob.set_val('parab_comp.x', 5.0)
    # prob.set_val('parab_comp.y', -2.0)

    # prob.run_model()
    # print(prob.get_val('parab_comp.f_xy'))