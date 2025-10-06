#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 17 18:25:35 2021

@author: marcus
"""

import numpy as np              # array functions and manipulation 
import numpy.matlib
import glob                     # searching files function
import os                       # filename manipulation
import pandas as pd


class ICEHist:
    """
    Opens history files for data extraction.
    Common use to read multiple histories: 
        histNames = ['outputPower0', 'inputPower0']
        H5 = H5read.H5Hist(subFolder)
        hists = H5.readHistories(histNames)
        
    hists is a dictionary of hist objects. hist objects have the data and time packaged together
    """
    def __init__(self, folder, fileName = 0):
        if fileName == 0:
            self.H5HistFiles = glob.glob(folder + '*.ice')
            if len(self.H5HistFiles) > 0:
                print('This is an ICEPIC data directory!')
        else:
            self.H5HistFiles = os.path.join(folder, '') + fileName
         
#        self.h5 = h5py.File(self.H5HistFile,'r')
        self.histList = [ os.path.splitext(os.path.basename(file))[0] for file in self.H5HistFiles]
        self.baseDir = os.path.join(folder, '')
#        self.tend,self.TSTEPS,self.dt = self._readTimeInfo()
#        self.hists = {}
        return
    
    def readHistory(self, histName):
        dset = pd.read_csv(self.baseDir + histName + '.ice',delim_whitespace=True)
        dset = dset.to_numpy()
        hist = self._genHistObject(dset)
        
        if hist != None: hist.readHistory(dset)
        hist.name = histName
        return hist
    
    def readHistories(self,histList=None):
        if histList == None:
            histList = self.histList
        if type(histList) is not list:
            histList = [histList]
        hists = {}
        for histName in histList:
            #print(histName)
            hists[histName] = self.readHistory(histName)
        return hists
    
    def clearHistories(self):
        self.hists = {}
        
    
    # private methods
    
    def _genHistObject(self,dset):
        s = dset.shape
        if False == 4:            # it's a line Vector History
            hist = LineVectorHistory()
        elif False:
            hist = ParticleTagHistory()
        elif False:
            hist = VectorHistory()
        elif s[1] == 2:          # it's a scaler History
            hist = ScalerHistory()
        return hist

class NotHistory():
    def __init__(self):
        self.data = None
        self.type = NotHistory
    
    def readHistory(self,dset):
        pass

class ScalerHistory():
    """
    hist data structure which contains the relevant attributes such as the data and the time vector
    """
    def __init__(self):
        self.data = None
        self.t = None
        self.dt = None
        self.TSTEPS = None
        self.type = 'ScalerHistory'
        
    def readHistory(self, dset):
        self.s = dset.shape
        self.data = np.array(dset[:,1])
        self.TSTEPS = self.s[0]
        self.t = np.array(dset[:,0])
        self.dt = self.t[1]-self.t[0]
        
        return self
    
class LineScalerHistory(ScalerHistory):
    def __init__(self,tend):
        super().__init__(tend)
        self.NL = None 
        self.type = 'LineScalerHistory'

class ParticleTagHistory(ScalerHistory):
    def __init__(self,tend):
        super().__init__(tend)
        self.NTAGS = None
        self.COMPS = None
    def readHistory(self, dset):
        super().readHistory(dset)
        self.NTAGS = self.s[1]
        self.COMPS = self.s[2]

class VectorHistory(ScalerHistory):
    def __init__(self,tend):
        super().__init__(tend)
        self.COMPS = None
        self.type = 'VectorHistory'
        
    def readHistory(self, dset): 
        super().readHistory(dset)
        self.COMPS = self.s[-1]
        return self
    
    def cart2Cyl(self,phis):
        # possible useful function
        pass

class LineVectorHistory(VectorHistory):
    def __init__(self,tend):
        super().__init__(tend)
        self.NL = None
        self.type = 'LineVectorHistory'
        
    def readHistory(self, dset):
        super().readHistory(dset)
        self.data = np.reshape(dset,(self.s[0], self.s[1],self.s[3]) )
        self.s = self.data.shape # [NSTEPS, DLENGTH,COMPONENTS]
        self.NL = self.s[1]
        return self


#folder = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/incomingData/ZipVolts/'
#histName = 'voltage11'
#H = ICEHist(folder)
#
#hists = H.readHistories()


