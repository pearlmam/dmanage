#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 14:02:02 2025

@author: marcus
"""

import numpy as np
import pandas as pd
import copy
import glob
import os
import tables
import time
from pathos.multiprocessing import Pool
from multiprocessing import shared_memory

import pickle
import psutil
import matplotlib as mpl
import matplotlib.pyplot as plt
# from multiprocessing import Pool, Process, shared_memory

import dmanage.dfmethods as dfm
from dmanage.unit import make_data_unit
from dmanage.plugins import vsim
from dmanage.utils import constants as c
from dmanage.dfmethods.plot import Plot
from dmanage.utils.utils import child_override


DataDir = make_data_unit(vsim.loader.VSim)
class MyDataDir(DataDir):
    def __init__(self,dataDir=None):
        super().__init__(dataDir)
        # define model specific attributes
        self.rfPowers = ['Pin','Pout','Pdc']
        self.Vdcs = ['Vdc1','Vdc0']
        self.Vrf = ['Vin','Vout']
        self.Plot = Plot()
        self.cmapPhase = 'twilight'
        
    @child_override    
    def get_scalar_vars(self, varList, theRange=[0.75, 1.0], dtype='Dict'):
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
    
    
    
    @child_override  
    def gen_summary(self, varList=[], ow=False, resDir=None):
        np.seterr(divide='ignore')
        if ow:
            # self.summaryData = pd.Series()
            self.summaryData = pd.DataFrame()
        #### get start and end times
        histName = 'Pout'
        DF = self.Hists.read_as_df(histName)
        tBuff = 10e-9
        tStart = dfm.signal.get_startup(DF, debug=False) + tBuff
        tend = self.Hists.tend
        if tStart>tend*0.9:
            tStart = tend*0.9
        self.add_to_summary({'tStart':tStart,'tend':tend})
        
        ##### get powers
        histNames = copy.deepcopy(self.rfPowers)
        powerAvgs = self.get_scalar_vars([histNames[1], 'PRF_AVG', 'VDC'])
        self.add_to_summary(powerAvgs)
        
        ##### get voltage and mag
        inputParams = self.get_scalar_vars(['BSTATIC', 'VDC'])
        self.add_to_summary(inputParams)
        
        #### currents
        currentNames = []
        relevantCurrents = ['Ianode', 'Icathode', 'Iemit']
        for partType in self.Parts.types:
            if not partType[-1] == 'T':
                currentNames = currentNames + [partType + relevantCurrent for relevantCurrent in relevantCurrents]
        currentAvgs = self.get_scalar_vars(currentNames)
        self.add_to_summary(currentAvgs)
        
        iAnodeTotal = 0
        for key,value in currentAvgs.items():
            if 'Ianode' in key:
                iAnodeTotal = iAnodeTotal + value
        iAnodeTotal = abs(iAnodeTotal)
        iEmit = self.get_scalar_vars('iCathode')['iCathode']
        self.add_to_summary({'iEmit':iEmit,'iAnodeTotal':iAnodeTotal})
        
        #### calculate efficiency, gain 
        PoutAvg = powerAvgs[histNames[1]]
        PinAvg = powerAvgs['PRF_AVG']
        VdcAvg = powerAvgs['VDC']
        gain = 10*np.log10(np.float64(np.divide(PoutAvg,PinAvg)))
        eff = PoutAvg/(PinAvg + VdcAvg*iAnodeTotal)*100
        self.add_to_summary({'eff':eff,'gain':gain})
        
        ##### spectral analysis
        freq = self.get_scalar_vars('FREQ')['FREQ']
        self.add_to_summary({'freq':freq})
        noiseStabilityLevel=-35
        maxFreq = 4.2e9
        maxPks=15
        histName = copy.deepcopy(self.Vrf[1])
        if self.Hists.check_dataset(histName, output=True)[0]:
            DF = self.Hists.read_as_df(histName, concat=True)
            DF = DF.iloc[DF.index.get_level_values('t')>tStart]
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
        stable = self.check_stability(histNamePower=histNames[1], histNameVoltage=self.Vrf[1], noiseLevel=noiseStabilityLevel, cutoff=cutoff, debug=False)
        noisePks = DFpks.iloc[DFpks.index<(1.9*freq)][DFpks.columns[0]]
        if len(noisePks) > 1:
            twoPks = noisePks.nlargest(2)
            noiseLevel = twoPks.iloc[1]
            sideband = twoPks.index[1] - twoPks.index[0]
        else:
            noiseLevel = -np.inf
            sideband = np.nan
        DFpks.index = freq-DFpks.index
        self.add_to_summary({'stable':stable,'noiseLevel':noiseLevel,'sideband':sideband})
        self.add_to_summary({'sidebands':DFpks})
        DF = self.gen_lookup_entry(varList=varList)
        self.add_to_summary(DF)
        
        
        ##### check for processed files
        
        ### rotating frame of reference
        relevantH5 = '_phi.t_freq-1'
        h5Files = glob.glob(self.baseDir+'*'+relevantH5+'*.h5')
        
        # step through each particles h5 file
        for h5File in h5Files:
            h5 = tables.open_file(h5File,'r')   # open h5 file
            # confirm it's correct is not implemented, just process it.
            h5RunLoc = os.path.normpath(h5.root._v_attrs.runLoc)
            # process file
            DF = pd.read_hdf(h5File)
            DF = DF.iloc[DF.index.get_level_values('t')>tStart]
            plotVars = DF.columns
            nSpokes = 3
            period = 2*np.pi/nSpokes
            phiRange = 'pi'
            particle = h5.root._v_attrs.particle
            
            ###### density mag
            densityMax = DF.max()
            iNames = ['max %s %s'%(particle,plotVar) for plotVar in densityMax.index]
            densityMax.index = iNames
            self.add_to_summary(densityMax)
            
            ###### wobble mag
            DFA = dfm.fft.fft(DF)
            DFA = dfm.fft.fft_amplitude(DFA, normalize=False)
            DFA = DFA.max()
            iNames = ['max %s %s'%(particle,plotVar) for plotVar in DFA.index]    
            DFA.index = iNames
            self.add_to_summary(DFA)
            for plotVar in plotVars:

                ##### spoke analysis
                phaseSpokes = self.getPhaseSpokes(DF[plotVar],refSignal='cos11',nSpokes=nSpokes,phiRange=phiRange,debug=False)
                phaseSpokes = phaseSpokes.interpolate(axis=0)
                phaseSpokes = dfm.signal.apply_filter(phaseSpokes, method='low', cutoff=freq)
                
                #### check for phase wrap
                locked = not (phaseSpokes.max()-phaseSpokes.min()).max()>(period*.95)
                self.add_to_summary({'lock':locked})
                
                if locked:
                    signalInfo = dfm.signal.get_signal_info(phaseSpokes)
                    signalInfoMean = signalInfo.mean()
                    signalInfoMean.index = [ i+' %s %s'%(plotVar,particle) for i in signalInfoMean.index]
                    self.add_to_summary({'%s %s'%(plotVar,particle):signalInfo})
                    self.add_to_summary(signalInfoMean)
                    
                    DFmean = dfm.helper.reduce(DF[plotVar],'t',method='mean')
                    DFmean.index = ((DFmean.index+2*np.pi)%(2*np.pi))
                    DFmean = DFmean.sort_index()
                    phase = dfm.signal.get_phase(DFmean, refSignal='cos11', period=period, hRatio=0.4, pRatio=0.3).iloc[0][0]
                    self.add_to_summary({'phaseSpoke %s %s'%(plotVar,particle):phase})
                    
                    ### get phase change of spokes 
                    # nRollPhaseChange = 10
                    ##########  plot phase change of spokes
                    title = 'dphi/dt RMS'
                    dt = phaseSpokes.index.get_level_values(0)[1]-phaseSpokes.index.get_level_values(0)[0] # assumes all same index
                    phaseChanges = phaseSpokes.diff(axis=0)*nSpokes/dt/2/np.pi
                    # phaseChanges = phaseChanges.rolling(nRollPhaseChange).mean()
                    phaseChangeRms = phaseChanges.pow(2).mean().pow(0.5)
                    phaseChangeRms = phaseChangeRms.mean()
                    self.add_to_summary({'dphi/dt %s %s'%(plotVar,particle):phaseChangeRms})
                    
                    
                    phaseWobble = self.getPhaseWobble(phaseSpokes,refPhase=0,refSignal='sin')
                    phaseWobble = phaseWobble.mean()[0]
                    self.add_to_summary({'phaseWobble %s %s'%(plotVar,particle):phaseWobble})
                else:
                    break
                h5.close()
                
        ### Lab frame of reference
        # relevantH5 = '_phi.t_freq-0'
        # h5Files = glob.glob(self.baseDir+'*'+relevantH5+'*.h5')
        
        # ##### now process them
        # # step through each particles h5 file
        # for h5File in h5Files:
        #     h5 = tables.open_file(h5File,'r')
            
        #     DF = pd.read_hdf(h5File)
        #     DF = DF.iloc[DF.index.get_level_values('t')>tStart]
        #     plotVars = DF.columns
        #     nSpokes = 3
        #     period = 2*np.pi/nSpokes
        #     phiRange = 'pi'
        #     particle = h5.root._v_attrs.particle
        #     #DF
            
            
        np.seterr(divide='warn')
        return self.summaryData
    
    def check_stability(self, histNamePower='Pout', histNameVoltage='Vout', noiseLevel=-35, cutoff=[0, 2.5e9], debug=False):
        
        startupBuff = 10e-9
        fftRange = [0.0,1.0]
        # filtRange = [0.0,1.0]
        minStart = 50e-9
        minSteady = 20e-9
        
        
        # histName = 'Pout'
        DF = self.Hists.read_as_df(histNamePower)
        tend = DF.index.get_level_values('t').max()
        tStart = dfm.signal.get_startup(DF, debug=False)
        tCut = tStart + startupBuff
        ###### check minumum times
        if minStart:
            if tStart > minStart:
                if debug:
                    print('start time less than threshold: %0.2f < %0.2f '%(tStart/1e9,minStart/1e9))
                stable = False
                return stable
            
        if minSteady:
            tSteady = tend - tStart
            if tSteady < (minSteady + startupBuff):
                if debug:
                    print('stable time less then threshold: %0.2f < %0.2f '%(tSteady/1e9,minSteady/1e9))
                stable = False
                return stable
        ###### check output power is not equal to input
        powerAvgs = self.get_scalar_vars(['PRF_AVG'])
        PoutAvg = DF.mean()[0]
        PinAvg = powerAvgs['PRF_AVG']
        if PoutAvg < 2*PinAvg:
            if debug:
                print('output power ~= input power, stable=NaN')
            stableP = np.nan
            return stableP
        
        ######## check FFT of voltage
        DF = self.Hists.read_as_df(histNameVoltage)
        DF = DF.iloc[DF.index.get_level_values('t')>tCut]
        stableV = dfm.signal.check_stability(DF, method='fft', cutoff=cutoff, noiseLevel=noiseLevel, debug=False)
        
        if debug:
            print('fft check range[%s]: stable=%0.0f'%(fftRange,stableV))
        return stableV
    
    def gen_lookup_entry(self, varList=None):
        if type(varList)==type(None): varList=self.relVars
        entryDict = self.get_scalar_vars(varList)
        #self.DFentries['runLoc']="'" + self.baseDir + "'"
        entryDict['runLoc']=self.baseDir
        DF = pd.DataFrame(entryDict,columns=['runLoc']+varList,index=[0])
        return DF
    
    #        PARTICLE BINNING STUFF
    #######################################################
    
    def gen_pos_vel_df(self, partTypes, binType='pos', steps=None, posBins=50, posCols=['r', 'phi', 'z'], velBins=50, velCols=['ur', 'uphi', 'uz'], freq=False, phiRange='2pi', ow=False, nc=1):
        conserveMem=True
        if not type(partTypes) is list:
            partTypes = [partTypes]
        tCol = 't'
        phiCol = 'phi'
        nSpokes=3
        sampleRatio=False
        DFPlist = []
        DFVlist = []
        for partType in partTypes:
            info = self.Parts.info[partType]
            DF = self.Parts.read_as_df(steps=steps, partType=partType, nc=nc)
            
            if not DF.empty:
                startTime = time.time()
                # determine number of cores for conversion, needs big DFs
                memConvertThresh = 10e9
                memDF = DF.memory_usage().sum()
                ncConvert = int(np.floor(memDF/memConvertThresh))+1
                
                print('  Converting Coordinates with %i cores...'%(ncConvert), end=' ')
                DF = dfm.convert.cart_to_cyl(DF, phiRange=phiRange, nc=ncConvert)
                if (type(freq) is bool):
                    if freq: freq = self.PreVars.read('FREQ')['FREQ']
                if freq !=0:
                    # ???
                    DF = self.rotRefFrame(DF,freqDetect=freq,tCol=tCol,phiCol=phiCol,discretePhi=False,phiRange=phiRange,nc=ncConvert)
                executionTime = (time.time()-startTime)
                print(' Done in %0.2f seconds'%(executionTime))
                
                if binType.lower()=='pos' or binType.lower()=='both':
                    print('  Binning Position with %i Cores...'%nc, end=' ')
                    startTime = time.time()
                    DFP = self.pos_bin_df(DF, info, posBins, posCols, phiRange=phiRange, conserveMem=conserveMem, nc=nc)
                    executionTime = (time.time()-startTime)
                    print(' Done in %0.2f seconds'%(executionTime))
                    DFPlist = DFPlist + [DFP]
                
                if binType.lower()=='vel' or binType.lower()=='both':
                    print('  Binning Velocity with %i Cores...'%nc, end=' ')
                    startTime = time.time()
                    DFV = self.vel_bin_df(DF, info, velBins, velCols, phiRange=phiRange, conserveMem=conserveMem, nc=nc)
                    # DF1 = self.DFM.intervalIndex2Num(DF1)
                    executionTime = (time.time()-startTime)
                    print(' Done in %0.2f seconds'%(executionTime))
                    DFVlist = DFVlist + [DFV]
        
        ncConcat = 1
        if len(partTypes) > 1: print('  weighted concat with %i Cores...'%ncConcat, end=' ')
        startTime = time.time()
        
        DFP = dfm.helper.weighted_concat(DFPlist, nc=ncConcat)
        DFV = dfm.helper.weighted_concat(DFVlist, nc=ncConcat)
        
        executionTime = (time.time()-startTime)    
        if len(partTypes) > 1: print(' Done in %0.2f seconds'%(executionTime))

        if binType.lower()=='pos':
            return DFP
        elif binType.lower()=='vel':
            return DFV
        elif binType.lower()=='both':
            return DFP,DFV


    def pos_bin_df(self, DF, info, bins=50, binCols=['r', 'phi', 'z'], phiRange='2pi', conserveMem=True, nc=1):
        if not type(bins) is list: bins = [bins]*len(binCols)
        if type(bins[0]) is list: binBreaks = bins
        elif len(binCols) != len(bins): raise Exception("length of bins must be 3 for the bin columns %s"%binCols)
        else: 
            binBreaks = dfm.helper.gen_bin_breaks(DF, binCols, bins, phiRange=phiRange)
        _posBinDF = dfm.wrapper.parallelize_df_method(self._pos_bin_df)
        DF = _posBinDF(DF,info,binBreaks,binCols,phiRange,conserveMem,nc=nc)
        return DF
        
        
    
    def _pos_bin_df(self, DF, info, bins=50, binCols=['r', 'phi', 'z'], phiRange='2pi', conserveMem=True):

        """
        keeping interval columns created by cut will remember the levels and keep zero values around. 
        However this generates a huge dataset; we may want to remove these zero values for efficiency in the future

        Parameters
        ----------
        DF : TYPE
            DESCRIPTION.
        bins : TYPE
            DESCRIPTION.
        info : TYPE
            DESCRIPTION.

        Returns
        -------
        DF : TYPE
            DESCRIPTION.

        """

        if not type(bins) is list: bins = [bins]*len(binCols)
        if type(bins[0]) is list: binBreaks = bins
        elif len(binCols) != len(bins): raise Exception("length of bins must be 3 for the bin columns %s"%binCols)
        else: 
            binBreaks = dfm.helper.gen_bin_breaks(DF, binCols, bins, phiRange=phiRange)

        # binBreaks = dfm.helper.genBinBreaks(self,DF,binCols,bins)
        ###### get relevant info
        preVars = self.PreVars.read(['R_CATHODE','R_CENTER_REGION','VDC'])
        # print(preVars)
        Vdc = preVars['VDC']
        rCathode = preVars['R_CATHODE']
        rAnode = preVars['R_CENTER_REGION']
        rInteraction = rAnode-rCathode
        

        DF = DF.sort_index()
        DF = DF.reset_index()
        if 'num' in DF.columns: DF.drop(columns=['num'])
        DF['ux'] = DF['r']*DF['uphi']
        
        uMag = np.sqrt(DF['ur']**2 + (DF['r']*DF['uphi'])**2) # for use in keTot and uMagMean
        DFB = dfm.helper.bin_df(DF, binCols, binBreaks)
        
        for i,binCol in enumerate(binCols):
            if DFB[binCol].isnull().values.all():
                binCols.pop(i)
        ##### Potential Energy
        
        C = Vdc/np.log10(rAnode/rCathode)
        Epot = (C*np.log10(DF['r'].clip(upper=rAnode))-C*np.log10(rAnode)+Vdc)*DF['weight']*c.eV2J   # for radial potential

        # Epot = Vdc/rInteraction*(DF['r'].clip(upper=rAnode)-rCathode)*DF['weight']*c.eV2J  # for linear potential
        wSum = DFB.groupby(['t']+binCols)['weight'].transform('sum') # grouped weighted sum
        
        DF = copy.deepcopy(DFB[ ['tag','t']+binCols+['weight']] )
        if conserveMem: DFB.drop('weight',inplace=True,axis=1)
        # DF = copy.deepcopy(DFB[ ['t']+binCols] )
        DF['urMean'] = DFB['ur']*DF['weight']/wSum       # will be mean when summed
        if conserveMem: DFB.drop('ur',inplace=True,axis=1)
        
        DF['uphiMean'] = DFB['uphi']*DF['weight']/wSum   # will be mean when summed
        if conserveMem: DFB.drop('uphi',inplace=True,axis=1)
        
        ######### unused stuff
        # DF['uRatio'] = (DFB['ur']/DFB['ux']).abs()*DFB['weight']/wSum
        # DF['urAcc'] = (DFB['ur']>0)*DFB['weight']
        # DF['urDec'] = (DFB['ur']<0)*DFB['weight']
        # DF['uphiAcc'] = (DFB['uphi']>0)*DFB['weight']
        # DF['uphiDec'] = (DFB['uphi']<0)*DFB['weight']
        
        DF['keTot']= 0.5*info['mass']*uMag**2*DF['weight']
        # temp = DF[['tag','keTot']].groupby('tag').transform('first')['keTot'] # initial Energy
        DF['energyTransfer'] = Epot-DF['keTot']  # -temp ignore initial energy
        temp = DF.groupby('tag')[['t','energyTransfer']].diff()   # dt and dEnergyTransfer
        DF['power'] = temp['energyTransfer']/temp['t']
        
        # DF['uMagMean'] = uMag*DFB['weight']/wSum
        DF.drop('tag',inplace=True,axis=1)
        DF = DF.groupby(['t']+binCols).sum() 
        DF = dfm.convert.interval_to_num_index(DF)
        return DF
    
    def vel_bin_df(self, DF, info, bins=50, binCols=['ur', 'uphi', 'uz'], phiRange='2pi', conserveMem=True, nc=1):
        if not type(bins) is list: bins = [bins]*len(binCols)
        if type(bins[0]) is list: binBreaks = bins
        elif len(binCols) != len(bins): raise Exception("length of bins must be 3 for the bin columns %s"%binCols)
        else: 
            binBreaks = dfm.helper.gen_bin_breaks(DF, binCols, bins, phiRange=phiRange)
        
        _velBinDF = dfm.wrapper.parallelize_df_method(self._vel_bin_df)
        DF = _velBinDF(DF,info,binBreaks,binCols,phiRange,conserveMem,nc=nc)
        return DF
    
    def _vel_bin_df(self, DF, info, bins=50, binCols=['ur', 'uphi', 'uz'], phiRange='2pi', conserveMem=True):
        if not type(bins) is list: bins = [bins]*len(binCols)
        if type(bins[0]) is list: binBreaks = bins
        else: 
            binBreaks = dfm.helper.gen_bin_breaks(DF, binCols, bins, phiRange)

        DF = DF.reset_index()
        if 'num' in DF.columns: DF.drop(columns=['num'])
        DFB = dfm.helper.bin_df(DF, binCols, binBreaks)
        
        # # check for uneeded bins
        # for i,binCol in enumerate(binCols):
        #     if DFB[binCol].isnull().values.all():
        #         binCols.pop(i)
        
        wSum = DFB.groupby(['t']+binCols)['weight'].transform('sum') # grouped weighted sum
        DF = copy.deepcopy(DFB[['t']+binCols+['weight']])
        if conserveMem: DFB.drop('weight',inplace=True,axis=1)
        # DF = copy.deepcopy(DFB[ ['t']+binCols ])
        DF['rMean'] = DFB['r']*DF['weight']/wSum       # will be mean when summed
        if conserveMem: DFB.drop('r',inplace=True,axis=1)
        DF['phiMean'] = DFB['phi']*DF['weight']/wSum   # will be mean when summed
        if conserveMem: DFB.drop('phi',inplace=True,axis=1)
        # DF['weight']=copy.deepcopy(DFB['weight'])          # will be count when summed
        DF = DF.groupby(['t']+binCols).sum()
        DF = dfm.convert.interval_to_num_index(DF)
        return DF     
    
    def get_correlated_images(self, DF, wlock, groupVars, tVar='t', filt=True, tRange=(None, None), nc=1):
        if not isinstance(wlock,(tuple, list,np.ndarray)):
            wlocks = [wlock]
        else:
            wlocks = wlock
        freqName = 'freq'
        if nc >1:
            DFs = np.array_split(DF,nc)
            variables = [(DF,wlock,groupVars,tVar,filt,tRange,1) for DF in DFs]
            pool = Pool(processes=nc)
            F =  pool.starmap_async(self.get_correlated_images, variables)
            DFTupleList = F.get()
            pool.close()
            DF0s,DF90s = list(zip(*DFTupleList))
            DF0s = pd.concat(DF0s)
            DF90s = pd.concat(DF90s)
            DF0s = DF0s.groupby(DF0s.index.names).sum().sort_index()
            DF90s = DF90s.groupby(DF90s.index.names).sum().sort_index()
        else:
            DF0s = []
            DF90s = []
            for wlock in wlocks:
                DF0,DF90 = self._get_correlated_images(DF, wlock, groupVars, tVar=tVar, filt=filt, tRange=tRange)
                DF0s = DF0s + [DF0]
                DF90s = DF90s + [DF90]
            DF0s = pd.concat(DF0s)
            DF90s = pd.concat(DF90s)
        
        return DF0s,DF90s
    
    def _get_correlated_images(self, DF, wlock, groupVars, tVar='t', filt=True, tRange=(None, None)):
        
        if isinstance(DF,str):
            shm = shared_memory.SharedMemory(name=DF)
            DF = pickle.loads(shm.buf) ### comment out for lowest mem but more cpu time
        else:
            shm = None
            # DF = DF
        if filt and isinstance(tRange,(tuple,list)):
            tStart = tRange[0]
            tEnd = tRange[1]
        if filt and tStart is None:
                tStart = 0.0
        if filt and tEnd is None:
                tEnd = self.Hists.tend
        
        if filt and isinstance(DF,pd.core.frame.DataFrame):
            # cut the range so that it is an integer multiple of the period
            flock = wlock/2/np.pi
            t0 = tEnd - np.floor((tEnd-tStart)*flock)/flock 
            I = DF.index.get_level_values(tVar) > t0
            DF = DF.iloc[I]
            # print('filtering using %s'%(tRange))
            # print(tRange)
            
            
        DF0 = self._correlate(DF,wlock=wlock,groupVars=groupVars,tVar=tVar,signal='sin')
        DF90 = self._correlate(DF,wlock=wlock,groupVars=groupVars,tVar=tVar,signal='cos')
        if isinstance(shm,shared_memory.SharedMemory):
            del DF 
            shm.close()
        
        # DF = DF.sort_index()
        return DF0,DF90
    
    def _correlate(self,DF,wlock,groupVars,tVar='t',signal='sin'):
        freqName = 'freq'
        if signal == 'sin':
            DF = DF.multiply(np.sin(wlock*DF.index.get_level_values(tVar).to_numpy()),axis=0)
        elif signal == 'cos':
            DF = DF.multiply(-np.cos(wlock*DF.index.get_level_values(tVar).to_numpy()),axis=0)
        flock = wlock/2/np.pi
        DF = DF.groupby(groupVars).sum().sort_index()
        indices = DF.index.names
        DF.insert(0,freqName,flock)
        DF.set_index([freqName],append=True,inplace=True)
        DF = DF.reorder_levels([freqName] + indices)
    
        return DF
        
    
    def _get_lockin_amp_phase(self, DF0, DF90):
        A = (DF0.pow(2) + DF90.pow(2)).pow(0.5)
        # P = np.arctan(DF0.divide(DF90))
        P = np.arctan2(DF0,DF90)
        return A,P
    
    def get_lockin_amp_phase(self, DF0, DF90, nc=1):
        if nc>1:
            DF0s = np.array_split(DF0,nc)
            DF90s = np.array_split(DF90,nc)
            theArgs = [(DF0,DF90) for DF0,DF90 in zip(DF0s,DF90s)]
            pool = Pool(processes=nc)
            F =  pool.starmap_async(self._get_lockin_amp_phase, theArgs)
            DFTupleList = F.get()
            pool.close()
            As,Ps = list(zip(*DFTupleList))
            A = pd.concat(As)
            P = pd.concat(Ps)
        else:
            A,P = self._get_lockin_amp_phase(DF0, DF90)
        
        return A,P
    
    
    def get_lockin_images(self, DF, flocks, posVars=['phi', 'r'], tVar='t', wCol='weight', cutoffWeight=0.03, parallelMethod='time', memLimit=128e9, nc=1):
        
        # parallelMethod = 'multiple' # uses multiple cores on each flock, low memory
        # parallelMethod = 'single' # uses single core on each flock, higher memory
        flocks = np.array(flocks)
        flocksDisplay = np.around(flocks/1e9,3)
        filt=True
        if parallelMethod.lower() == 'freq' and nc>1:

            #### calculate mem usage to determine number of cores  
            nCopys = 3              # this is the estimated number of copys
            operationBuffer = 2     # some operations require extra memory on this order 
            memDF = DF.memory_usage().sum()
            memEstCore = memDF*(nCopys + operationBuffer)# estimated memory usage per core
            memAvail = psutil.virtual_memory().available
            memLimit = min(memLimit,memAvail)  # check if memory limit is greater than availiable memory
            ncPossible = int(np.floor(memLimit/memEstCore))
            nc = int(min(nc,len(flocks),ncPossible)) # number of cores must be less than or equal to the number of flocks
        if nc > 1:
            methodStr = 's using %s split method'%parallelMethod
        else:
            methodStr = ''
            
        print("  Calculating %i lock-in images with %i core%s... \n    flocks=%s GHz"%(len(flocks),nc,methodStr,flocksDisplay))
        startTime = time.time()
        
        if not wCol is None:
            weight = DF[wCol].groupby(posVars).sum().sort_index()
            weightMax = weight.max()
            weightMin = weight.min()
            cutoffWeightValue = cutoffWeight*(weightMax-weightMin)+weightMin
            cutRegion = weight < cutoffWeightValue
        else:
            cutRegion = []
        
        tStart = DF.index.get_level_values(tVar).min()
        tEnd = DF.index.get_level_values(tVar).max()
        tRange = [tStart,tEnd]
        if nc > 1:

            if parallelMethod.lower() == 'freq':
                # parallelMethod.lower() == 'single':
                flocksList = np.array_split(flocks,nc)
                
                pickled_df = pickle.dumps(DF)
                size = len(pickled_df)
                shm = shared_memory.SharedMemory(create=True, size=size)
                shm.buf[:size] = pickled_df
                variables = [(shm.name,flock,posVars,tVar,filt,tRange,1) for flock in flocksList]
                
                # variables = [(DF,flock,posVars,cutRegion,filt,False,1) for flock in flocks]
                pool = Pool(processes=nc)
                F =  pool.starmap_async(self._get_lockin_images, variables)
                DFTupleList = F.get()
                pool.close()
                As,Ps = list(zip(*DFTupleList))
                As = pd.concat(As)
                Ps = pd.concat(Ps)
            elif parallelMethod.lower() == 'spatial':
                # splitSpatial
                DFs = dfm.helper.split_by(DF, nc, posVars)  # spatial Split
                variables = [(DF,flocks,posVars,tVar,filt,tRange,1) for DF in DFs]
                pool = Pool(processes=nc)
                F =  pool.starmap_async(self._get_lockin_images, variables)
                DFTupleList = F.get()
                pool.close()
                As,Ps = list(zip(*DFTupleList))
                
                As = pd.concat(As)
                Ps = pd.concat(Ps)

            elif parallelMethod.lower() == 'time':
                # splitTime
                As,Ps = self._get_lockin_images(DF=DF, flocks=flocks, posVars=posVars, tVar=tVar, filt=filt, tRange=tRange, nc=nc)
        else:
            As,Ps = self._get_lockin_images(DF=DF, flocks=flocks, posVars=posVars, tVar=tVar, filt=filt, tRange=tRange, nc=1)
        flocksProcessed = As.index.get_level_values('freq').unique()
        flocksUnprocessed = set(flocksProcessed) ^ set(flocks)
        if len(flocksUnprocessed)>0:
            print('unprocessed frequencies detected: %s'%flocksUnprocessed)
        As.iloc[np.tile(cutRegion,len(flocksProcessed))]=np.nan
        Ps.iloc[np.tile(cutRegion,len(flocksProcessed))]=np.nan
        executionTime = (time.time() - startTime)/60.
        print('  Done in %0.2f minutes'%(executionTime))
        # As.loc[cutRegion]=np.nan
        # Ps.loc[cutRegion]=np.nan
        return As,Ps
    
    def _get_lockin_images(self, DF, flocks, posVars=['phi', 'r'], tVar='t', filt=True, tRange=(None, None), nc=1):
        
        nSpokes = 3
        freqName = 'freq'
        
        if filt and isinstance(tRange,(tuple,list)):
            tStart = tRange[0]
            tEnd = tRange[1]
        if filt and tStart is None:
                tStart = 0.0
        if filt and tEnd is None:
                tEnd = self.Hists.tend
                
        
        
        wlocks = 2*np.pi*np.array(flocks)
        DF0,DF90 = self.get_correlated_images(DF, wlock=wlocks, groupVars=posVars, filt=filt, tRange=tRange, nc=nc)

        
        flocks = DF0.index.get_level_values(0).unique()
        As,Ps = self.get_lockin_amp_phase(DF0, DF90, nc=nc)
       
        
        return As,Ps
    
    def prep_polar_fig(self, ax, cbar, cbarRemove=False):
        ax.set_yticks([2.0,3.0])
        ax.set_yticklabels([])
        ax.xaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%.2f'))
        xticks = [0,np.pi/2,np.pi,np.pi*3/2]
        ax.set_xticks(xticks)
        ax.set(ylim=[0,3])
        #### default xticks uses degrees
        
        
        ##### use radian labels with 2 decimal places
        # labels = [str(round(float(xtick), 2)) for xtick in xticks]
        # ax.set_xticklabels(labels)
        
        ##### Use no labels
        ax.set_xticklabels([])
        
        if (not cbar is None) and cbarRemove:
            cbar.remove()
        return ax,cbar
    
    def plot_lockin_image(self, A, P, saveName, saveLoc=None, saveTag='', cbar=True, clim=None, bbox='tight', fig=1):
        cbarRemove = not cbar
        cbarOrientation='horizontal'
        figsize = (16,8)# for paired
        # figsize = (9,8)  # for individual
        if cbarOrientation=='horizontal':
            minShift=[0.,0.11]
            
        else:
            minShift=[0.,0.13]
            
        if cbarRemove:
            wspace=.01
        else:
            wspace=-.09
            
        
        def getbbox(bbox,ax=None,cbar=None,minShift=[0.,0.],maxShift=[1.,1.]):
            if bbox == 'tight':
                pass
            elif bbox == 'shrink':
                plotBbox = np.array(ax.get_tightbbox())
                if cbar.ax.figure is None:
                    bbox_min = np.min(np.array([plotBbox[0]]),axis=0)
                    bbox_max = np.max(np.array([plotBbox[1]]),axis=0)
                else:
                    cbarBbox = np.array(cbar.ax.get_tightbbox())
                    bbox_min = np.min(np.array([plotBbox[0],cbarBbox[0]]),axis=0)
                    bbox_max = np.max(np.array([plotBbox[1],cbarBbox[1]]),axis=0)
                
                bbox_extents = bbox_max - bbox_min
                bbox_minShift = bbox_extents*np.array(minShift) + np.array([-5,0])  # percentage shift + pixel shift
                bbox_maxShift = bbox_extents*(np.array([1.,1.])-np.array(maxShift)) - np.array([5,5])
                bbox_min = bbox_min + bbox_minShift
                bbox_max = bbox_max - bbox_maxShift
                bbox = mpl.transforms.Bbox([bbox_min,bbox_max])
                bbox = mpl.transforms.Bbox(mpl.transforms.TransformedBbox(bbox, mpl.transforms.Affine2D().scale(1./fig.dpi)))
            else:
                pass
            return bbox
        def combinebboxes(bboxes):
            points = []
            for bbox in bboxes:
                points = points + [bbox.get_points()]
            stackedPoints = np.concatenate(points,axis=0)
            lowerPoint = stackedPoints.min(axis=0)
            upperPoint = stackedPoints.max(axis=0)
            bbox = mpl.transforms.Bbox([lowerPoint,upperPoint])
            return bbox
        
        
        plotVars = A.columns
        baseLoc=saveLoc
        if type(baseLoc)==type(None): 
            baseLoc=self.resDir
        # saveLoc = baseLoc + 'processed/particles/%s/%s/lockIn/'%(partTypes[0],FORstring)    
        baseLoc = '%s/lockIn/'%(baseLoc)
        if not os.path.exists(baseLoc):
            # ??? there's a race condition here with multiple processes where another process might create a dir
            # wrap this function with a non error raising mkdir. 
            try: os.makedirs(baseLoc) 
            except: pass
        if len(saveTag) > 0:
            if not saveTag[0] == '_':
                saveTag = '_' +  saveTag
        else:
            saveTag = ''
        baseName = saveName
        
        for plotVar in plotVars:
            saveLoc = '%s/%s/'%(baseLoc,plotVar)
            if not os.path.exists(saveLoc):
                os.makedirs(saveLoc) 
            figNum = fig
            saveName = '%s_%s'%(baseName,plotVar)
            
            if clim is None:
                clim = (A[plotVar].min(), A[plotVar].max())
            elif isinstance(clim, (list, tuple)):
                clim = list(clim)
                if clim[0] is None:
                    clim[0] = A[plotVar].min()
                if clim[1] is None:
                    clim[1] = A[plotVar].max()
            else:
                pass
            saveNameAP = saveName + saveTag
            subplot=0
            variable = '-A'
            saveNameA = saveName + variable + saveTag
            fig,axs,plot,cbar = self.Plot.pcolor(A[plotVar],figsize=figsize,polar=True,subplots=(1,2),subplot=subplot,fig=figNum,cbarOrientation=cbarOrientation)
            if cbarRemove==True or cbarOrientation=='horizontal':
                plt.subplots_adjust(wspace=wspace)
            ax = axs[subplot]
            #ax.set(title='%s(%s)'%(variable,baseName))
            ax.set_title("")
            
            ax,cbar = self.prep_polar_fig(ax, cbar, cbarRemove)
            cbar.mappable.set_clim(clim[0], clim[1])
            #cbar.set_label('(arb.)', rotation=270,labelpad=30)
            bboxA = getbbox(bbox,ax=ax,cbar=cbar,minShift=minShift)
            # fig.savefig(saveLoc + saveNameA + '.' + self.Plot.P.saveType, bbox_inches=bbox, format=self.Plot.P.saveType)
            #figNum = figNum+1
            subplot=1
            variable = '-P'
            saveNameP = saveName + variable + saveTag
            fig,axs,plot,cbar = self.Plot.pcolor(P[plotVar],figsize=figsize,polar=True,subplots=(1,2),subplot=subplot,fig=figNum,clear=False,cmap=self.cmapPhase,cbarOrientation=cbarOrientation)
            ax = axs[subplot]
            #ax.set(title='%s(%s)'%(variable,baseName))
            ax.set_title("")
            
            ax,cbar = self.prep_polar_fig(ax, cbar, cbarRemove)
            if not cbarRemove:
                cbar.set_ticks([-3.14, -np.pi/2, 0,np.pi/2, 3.14])
                if cbarOrientation=='horizontal':
                    cbar.ax.set_xticklabels([r'-$\pi$', r'-$\dfrac{\pi}{2}$', 0,r'$\dfrac{\pi}{2}$',r'$\pi$'])
                else:
                    cbar.ax.set_yticklabels([r'-$\pi$', r'-$\dfrac{\pi}{2}$', 0,r'$\dfrac{\pi}{2}$',r'$\pi$'])
            
            #cbar.set_label('(rad)', rotation=270,labelpad=10)
            bboxP = getbbox(bbox,ax=ax,cbar=cbar,minShift=minShift)
            if isinstance(bboxA,str):
                bbox = bboxA
            else:
                bbox = combinebboxes([bboxA,bboxP])
            
            # fig.savefig(saveLoc + saveNameP + '.' + self.Plot.P.saveType, bbox_inches=bbox, format=self.Plot.P.saveType)
            fig.savefig(saveLoc + saveNameAP + '.' + self.Plot.P.saveType, bbox_inches=bbox, format=self.Plot.P.saveType)
            
            #figNum = figNum+1
        return fig,axs,plot,cbar
        
    def plot_lockin_images(self, A, P, saveLoc=None, saveTag='', cbar=True, clim=None, bbox='tight', fig=1, nc=1):
        if issubclass(type(A), pd.core.series.Series):
            A = pd.DataFrame(A)
        if issubclass(type(P), pd.core.series.Series):
            P = pd.DataFrame(P)
        startTime = time.time()
        outputProgress = True
        freqName = 'freq'
        flocks = np.array(A.index.get_level_values(freqName).unique())
        nc = min(nc,len(flocks))
        baseLoc=saveLoc
        if type(baseLoc)==type(None): 
            baseLoc=self.resDir
        # saveLoc = baseLoc + 'processed/particles/%s/%s/lockIn/'%(partTypes[0],FORstring)    
        # baseLoc = '%s/lockIn/'%(baseLoc)
        # if not os.path.exists(baseLoc):
        #     os.makedirs(baseLoc) 
        
        if len(saveTag) > 0:
            if not saveTag[0] == '_':
                saveTag = '_' +  saveTag
        else:
            saveTag = ''
            
        
        # plotting
        # if dbMaxFreq is None or False:
        #     pass
        # else:
        #     # find max at the 
        #     A = 10*np.log10(A/dbMax)
        
        if outputProgress:
            flocksDisplay = np.around(flocks/1e9,3)
            Nflocks = len(flocks)
            print('  Plotting %i lock-in images with %i cores... \n    flocks=%s GHz'%(len(flocks),nc,flocksDisplay))
            
        
        if nc > 1:
            backend = mpl.get_backend()
            self.Plot.P.use('Agg')
            saveNames = ['f-%0.3fGHz'%(flock/1e9) for flock in flocks]
            
            variables = [(A.loc[flock],P.loc[flock],'f-%0.3fGHz'%(flock/1e9),baseLoc,saveTag,cbar,clim,bbox,i+fig) for i,flock in enumerate(flocks)]
            pool = Pool(processes=nc)
            F =  pool.starmap_async(self.plot_lockin_image, variables)
            F.get()
            pool.close()
            self.Plot.P.use(backend)
        else:
            print('    Progess: 0/%i'%(Nflocks),end='')
            for i,flock in enumerate(flocks):
                
                saveName = 'f-%0.3fGHz'%(flock/1e9)
                fig,ax,plot,cbar = self.plot_lockin_image(A.loc[flock], P.loc[flock], saveName=saveName, saveLoc=baseLoc, saveTag=saveTag, cbar=cbar, clim=clim, bbox=bbox)
                if outputProgress: 
                    print('\r    Progess: %i/%i'%(i+1, Nflocks),end='')
                
        executionTime = (time.time() - startTime)/60.
        if outputProgress: 
            print('  Done in %0.2f minutes'%(executionTime))
    
if __name__ == "__main__":
    
    folder = '../test_data/vsim_data/VDC-87.8e3/'
    DD = MyDataDir(folder)
    
    ##### test the summary generation
    names = ['Pout', 'VDC', 'electronsIanode']
    scalarVars = DD.get_scalar_vars(names)
    
    
    summaryData = DD.gen_summary(names)
    
    
    ##### test the particle binning
    nc = 4
    partType = 'electronsT'
    posBins = [100,150]
    velBins = [100,150]
    posCols = ['r','phi']
    velCols = ['uphi','ur']
    cutoffWeight = 0.01     # for plotting, set values below to NaN
    
    
    DFP = DD.gen_pos_vel_df(partType, binType='pos', steps=None, posBins=posBins, posCols=posCols, velBins=velBins, velCols=velCols, freq=False, phiRange='2pi', ow=False, nc=nc)
        
    ##### test the lock in ploting
    flocks = []
    
    # get steady state
    histName = 'Pout'
    DF = DD.Hists.read_as_df(histName)
    tend = DF.index.get_level_values('t').max()
    tStart = dfm.signal.get_startup(DF, debug=False) + 10e-9
    
    DF1 = DFP.iloc[DFP.index.get_level_values('t')>tStart].copy()
    
    freq = DD.get_scalar_vars('FREQ')['FREQ']
    flocks = [freq,freq/2,freq/3,freq/4]
    plotVars = ['weight', 'keTot','urMean','uphiMean','energyTransfer','power']         
    A,P = DD.get_lockin_images(DF1[plotVars], flocks, posVars=['phi', 'r'], cutoffWeight=cutoffWeight, nc=nc)
    maxA = A.max()
    np.seterr(divide='ignore')
    A = 20*np.log10(A/maxA)
    np.seterr(divide='warn')
    clim = (-30,0)
    # clim = (None,None)
    baseLoc = './processed/'
    saveTag = ''
    DD.plot_lockin_images(A, P, saveLoc=baseLoc, saveTag=saveTag, clim=clim, nc=nc)
    pass
    
    
    