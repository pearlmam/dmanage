#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Mon May 10 16:14:34 2021
SweepDir
@author: marcus
"""

import dataDir
import H5read
import os
import numpy as np
import time
import matplotlib.pyplot as plt
import pandas as pd

from scipy.interpolate import interp2d
import copy
from multiprocessing import Pool
import multiprocessing as mp
from functions import saveMp4
from functions import checkActiveProcs
import natsort
import glob
import dataMethods as dm
from time import sleep
import matplotlib as mpl

import bokeh as bk

class SweepDataDir(dm.MethodWrapper):
    """
    opens a sweep data directory containing VSim data directories for common analysis I use. 
    Plotting relevant histories, plotting electrons, sweep data, etc
    Can generate a data managment lookup spreadsheet to visualize the availiable data directories
    
    Inputs:
        baseDir: <string>, path to the data directory
        relHAPlots: <Dict>, the format must look like this: { plotTitle:{'histNames':histNames, 'movAvg':movAvg, 'ylabel':ylabel }
                  if an entry is excluded, no error is thrown until you use that entry}
        
    """
    
    def __init__(self,baseDir, relHAPlots=None, relEAPlots=None, visit=None,quickOpen=False,baseNameDepth=3):
        # sweep data directories
        print('Opening %s...'%baseDir, end = ' ')
        startTime = time.time()
        self.baseDir = os.path.join(baseDir,'')
        if not quickOpen:
            self.sweepDirs = self.getDDs(baseDir,nc=1)
            if len(self.sweepDirs) == 0: raise Exception("There are no Data Directories in '%s'"%self.baseDir)
            self.sweepDirs = natsort.natsorted(self.sweepDirs)
            self.DD = dataDir.DataDir(self.baseDir+self.sweepDirs[0])
        else:
            self.sweepDirs = []
        self.resDir = self.baseDir + 'processed/' # result directory
        self.sweepResDir = self.resDir + 'sweep/'
        self.sweepDataSaveName = 'sweepData'
        self.sweepDataSaveLoc = self.baseDir
        self.resScalerPlotDirs = []
        self.saveType = 'png'
        self.relHAPlots = relHAPlots
        self.relEAPlots = relEAPlots
        self.visit=visit
        self.debug = False
        self.dataLookupFile = self.baseDir + 'dataLookup.xlsx'
        self.DFM = dm.DFMethods()
        self.P = dm.PlotDefs()
        self.baseNameDepth=3
        # remove processed directory from list
        try: self.sweepDirs.remove('processed')
        except: pass
        executionTime = time.time()-startTime
        print('Done in %0.3f Seconds'%executionTime)
#        # generate result directories
#        for i,plotType in enumerate(self.relPlots):
#            self.resScalerPlotDirs.append(self.resDir + plotType + '/')
#            if not os.path.exists(self.resScalerPlotDirs[i]):
#                os.makedirs(self.resScalerPlotDirs[i])

    
    def _getDDs(self,subDirs):
        sweepDirs = []
        # print(subDirs)
        remDirStrings = ['processed']
        if type(subDirs) != list: subDirs = [subDirs]
        for root in subDirs:
            # print(root)
            skip = False
            for remDirString in remDirStrings:
                if remDirString in root:
                    skip = True
            
            if H5read.isVSim(root) and not skip: sweepDirs.append(root.replace(self.baseDir,''))
            else: pass
            
        return sweepDirs
        
    def getDDs(self,baseDir=None,nc=1):
        
        if type(baseDir) == type(None):
            baseDir = self.baseDir
        subDirs = list(list(zip(*os.walk(baseDir,followlinks=True)))[0])
        # print(type(subDirs))
        if nc > 1:
            pool = Pool(processes=nc)
            result = pool.map_async(self._getDDs,subDirs)
            result.wait()
            sweepDirsList = result.get()
            pool.close()
            sweepDirs = [x for l in sweepDirsList for x in l]  
        else:
            sweepDirs = self._getDDs(subDirs)

        return sweepDirs
        
    def genBaseName(self,theInput,depth=10):
        """
        theInput can be of type string or dict
        """
        if type(theInput) is str:
            if self.baseDir in theInput: theInput=theInput.replace(self.baseDir,'')
            theInput = theInput.rstrip('/')
            theInput = theInput.split('/')[-depth:]
            baseName = '_'.join(theInput)
            # baseName = theInput.replace('/','_')  
        elif type(theInput) is dict:
            baseName = ''
            for name,value in theInput.items():
                baseName = baseName + '_%s-%s'%(name,value)
            baseName = baseName[1:]
        elif issubclass(type(theInput), pd.core.frame.DataFrame):
            pass
        elif issubclass(type(theInput), pd.core.indexes.multi.MultiIndex):
            names = theInput.names
            
        return baseName
    
    def getVarsFromDir(self,folder,dtype='DataFrame',Nrepeat=1,depth=10):
        if self.baseDir in folder: folder=folder.replace(self.baseDir,'')
        folder = folder.rstrip('/')
        varNames = folder.split('/')[-depth:]
        Dict = {}
        for varName in varNames:
            temp = varName.split('-',1)   # only split first occurance
            if len(temp) == 2:
                name = temp[0]
                value = temp[1]
                try: value = float(value)
                except: pass
                Dict[name]=[value]*Nrepeat
            else:
                pass # not a variable or proper format
        if dtype.lower() == 'dict':
            return Dict
        elif dtype.lower() == 'list':
            return list(Dict.keys()),list(Dict.values())
        else:
            return pd.DataFrame(Dict)
    
    def getVarsFromMI(self,mi,dtype='DataFrame'):
        iNames = mi.names
        Dict = {} 
        for iName in iNames:
            Dict[iName] = list(mi.get_level_values(iName))
            
        if dtype == 'Dict':
            return Dict
        elif dtype == 'List':
            return list(Dict.keys()),list(Dict.values())
        else:
            return pd.DataFrame(Dict)
        
        
    def combineDicts(self,dictList):
        for i,dictionary in enumerate(dictList):
            if i == 0:
                outDict = dictionary
            else:
                for key in dictionary.keys():
                    if not type(outDict[key]) is list: outDict[key] = [outDict[key]]
                    if not type(dictionary[key]) is list: dictionary[key] = [dictionary[key]]
                    outDict[key] = outDict[key] + dictionary[key]
        return outDict
    
    def getVarsFromDirs(self,folders):
        DFList = []
        for folder in folders:
            DFList = DFList + [self.getVarsFromDir(folder)]
        DF = pd.concat(DFList)
        return DF    
        
    def getRelVars(self,relVars):
        if not type(relVars) is list: relVars = [relVars]
        DFList = []
        for sweepDir in self.sweepDirs:
            DD = dataDir.DataDir(self.baseDir + sweepDir)
            DF = DD.getScalerVars(relVars,dtype='DF')
            DF['sweepDir'] = sweepDir
            DFList = DFList + [DF]
        DF = pd.concat(DFList)
        DF = DF.set_index('sweepDir')
        return DF
    
    
    
    def getRelSweepDirs(self,relVarsConds, logic='and'):
        
        DF = self.getRelVars(relVarsConds.keys())
        for key,value in relVarsConds.items():
            check = True
            if key == 'le':
                check = DF[key]<=value
            elif key == 'ge':
                pass
            elif key == 'gt':
                pass
            elif key == 'lt':
                pass
            elif key == 'equal':
                pass
        
        
        
        
    def h52csv(self,saveLoc = None):
        if saveLoc == None: saveLoc = self.resDir
        if not os.path.exists(saveLoc):
            os.makedirs(saveLoc)
        for sweepDir in self.sweepDirs:
            sweepDir = os.path.join(sweepDir,'')
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            DD.h52csv(saveLoc)
    
    def _saveParticleJpegsVisit(self,sweepDir, partTypes,saveLoc=None,delay=0):
        """
        delay is needed because the function cant save multiple videos if the command is called at the same time. The calls are staggered
        """
        if not type( partTypes) is list:  partTypes = [ partTypes]
        sweepDir = os.path.join(sweepDir,'')
        baseName = self.genBaseName(sweepDir)
        if type(saveLoc)==type(None): saveLoc=self.resDir
        time.sleep(delay)
        
        DD = dataDir.DataDir(self.baseDir + sweepDir,visit=self.visit)
        subProc = DD.saveParticleJpegsVisit( partTypes= partTypes,saveLoc=saveLoc,saveTag=baseName,ticks=False,freq=0)
        subProc.wait()
        subProc.terminate()
        return subProc
        
    def saveParticleJpegsVisit(self, partTypes,saveLoc=None,nc=1,runAgain=True):
        if saveLoc==None: saveLoc=self.resDir
        if not type( partTypes) is list:  partTypes = [ partTypes]
 
        print('\n***********    Saving %s Videos     *******************\n'% partTypes)
        
        # parallel implementation:doesnt work correctly because the blocking subprocess calls dont play nice
        if nc>1:
            variables = []
            delay = 5
            for i,sweepDir in enumerate(self.sweepDirs):
                variables = variables + [(sweepDir,  partTypes, None, i%nc*delay)]
                # self._saveParticleJpegs(sweepDir, partTypes,None,i*10)   # for testing
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._saveParticleJpegs,variables)
            result.wait()
            # result.get()
            # time.sleep(1)
            pool.close()
            if runAgain: 
                print('\n***********    double Checking %s Videos     *******************\n'% partTypes)
                result = self._saveParticleJpegs( partTypes,saveLoc,nc,runAgain=False)
        else:
            # this is actually NOT serial if the wait command is not implemented. It will step through and submit until finished with no control over the num procs
            for i,sweepDir in enumerate(self.sweepDirs):
                subProc= self._saveParticleJpegsVisit(sweepDir, partTypes,saveLoc=saveLoc,delay=delay)
                # subProc.wait()
                # subProc.terminate()
                # time.sleep(10)  # wait for the last process to start.
        return 0
        
    # def _saveParticlesImgs(self,sweepDir, partTypes=None,saveLoc=None,freq=False,cCol=None,frameSkip=1,write=True,ow=False):
    #     """
    #     delay is needed because the function cant save multiple videos if the command is called at the same time. The calls are staggered
    #     """
    #     sweepDir = os.path.join(sweepDir,'')
    #     baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
    #     if type(saveLoc)==type(None): saveLoc=self.resDir
    #     print("generating pngs: '.../%s', freq=%s, partTypes=%s..."%(sweepDir,freq,partTypes),end='\n')
    #     startTime = time.time()
    #     DD = dataDir.DataDir(self.baseDir + sweepDir,visit=self.visit)
    #     bs,saveNames = DD.saveParticlesImgs( partTypes= partTypes,saveLoc=saveLoc,saveTag=baseName,freq=freq,cCol=cCol,frameSkip=frameSkip,write=write,ow=ow)
    #     executionTime = (time.time() - startTime)/60.0
    #     print('Done in %0.2f minutes'%(executionTime))
    #     return bs,saveNames
        
    def saveParticlesImgs(self, partTypes=None,sweepDirs=None,saveLoc=None,freq=False,cCol=None,ow=False,sweepVars=None,nc=1):
        if sweepDirs==None: sweepDirs=self.sweepDir
        if saveLoc==None: saveLoc=self.resDir
        sweepDirs = [sweepDir.replace(self.baseDir,'') for sweepDir in sweepDirs]

        # if type( partTypes) == type(None):  partTypes = 
        if type( partTypes) == type(None): output = 'all particle'
        else: output =  partTypes
        
        self.P.use('agg')
       
        for i,sweepDir in enumerate(sweepDirs):
            sweepDir = os.path.join(sweepDir,'')
            
            
            if type(saveLoc)==type(None): saveLoc=self.resDir
            print("generating pngs: '.../%s', freq=%s, partTypes=%s..."%(sweepDir,freq,partTypes),end='\n')
            startTime = time.time()
            DD = dataDir.DataDir(self.baseDir + sweepDir,visit=self.visit)
            if sweepVars is None:
                baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
            elif type(sweepVars) is list:
                sweepVarsDict = DD.getScalerVars(sweepVars)
                numDecimals = 3
                sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
                baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
            elif type(sweepVars) is dict:
                numDecimals = list(sweepVars.values())
                sweepVars = list(sweepVars.keys())
                sweepVarsDict = DD.getScalerVars(sweepVars)
                sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
                baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
            bs,saveNames = DD.saveParticlesImgs( partTypes=partTypes,saveLoc=saveLoc,saveTag=baseName,freq=freq,cCol=cCol,ow=ow)
            executionTime = (time.time() - startTime)/60.0
            print('Done in %0.2f minutes'%(executionTime))
            return bs,saveNames
        self.P.use()        
        return 0
        
        
    def saveMp4s(self,resDir=None,picType='png',overwrite=False):
        if type(resDir)==type(None): 
            resDir=self.resDir
        for root,dirs,files in os.walk(resDir):
            if 'videos' in os.path.basename(root):
                
                # for directory in dirs:
                for root,dirs,files in os.walk(root):
                    # path = os.path.join(root,directory,'') 
                    path = os.path.join(root,'')
                    imgs = glob.glob(path + '*.' + picType)
                    
                    # saveTag = os.path.basename(os.path.normpath(root)).replace('video','')
                    if len(imgs)>0:
                        fileName = os.path.basename(imgs[0])
                        saveTag = fileName.split('_')[1:-1]
                        
                        if len(saveTag)>0: saveTag = '_'+'_'.join(saveTag)
                        else: saveTag = ''
                        baseName = fileName.split('_')[0]
                        saveName = baseName + saveTag
                        shortPath = path.replace(self.baseDir,'.../')
                        print("Generating video in '%s'"%(shortPath))
                        result = saveMp4(path,saveName,overwrite=overwrite)
        return 0
    
    def getHistory(self,histNames,varDepth=3,nc=1):
        print('Getting Histories: %s...'%histNames, end=' ')
        startTime = time.time()
        nc = min(len(self.sweepDirs),nc)
        if nc > 1:
            sweepDirss = np.array_split(self.sweepDirs,nc)
            variables = [(histNames,sweepDirs,varDepth) for sweepDirs in sweepDirss]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._getHistory,variables)
            result.wait()
            DF = result.get()
            pool.close()
            DF = pd.concat(DF, axis=1)
        else:
            DF = self._getHistory(histNames,varDepth=varDepth)
        
        executionTime = time.time()-startTime
        print('Done in %0.3f seconds'%executionTime)
        return DF
    
    def _getHistory(self,histNames,sweepDirs=None,varDepth=3):
        if not type(histNames) is list:
            histNames = [histNames]
        if sweepDirs is None:
            sweepDirs = self.sweepDirs
        """
        varDepth: for column naming
        """
        DFs = []
        for sweepDir in sweepDirs:
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            DF = DD.Hists.readManyAsDF(histNames)
            sweepVars = self.getVarsFromDir(sweepDir,dtype='dataframe',Nrepeat=1,depth=varDepth)
            histNameI = pd.DataFrame({'histName':histNames})
            I = pd.concat([histNameI,sweepVars],axis=1).fillna(method='ffill')
            DF.columns = pd.MultiIndex.from_frame(I)
            DFs = DFs + [DF]
        DFs = pd.concat(DFs,axis=1)
        DFs = DFs.sort_index(axis=1)
        return DFs
    
    def plotHistoryDF(self,DF,saveName=None,saveLoc=None,ylim=(None,None),plotType='single',nc=1,**line2Dkwargs):
        if saveLoc==None: saveLoc=self.resDir + '/histories/'
        if not os.path.exists(saveLoc):
            os.makedirs(saveLoc)
            
        histNames = list(DF.columns.get_level_values('histName').unique())
        print('Plotting Histories: %s...'%histNames, end=' ')
        startTime = time.time()
        
        if nc > 1:
            if isinstance(ylim,(tuple, list)):
                ylimPlot = ylim
            else:
                ylimMin = DF.groupby(level=0,axis=1).min().min(axis=0)
                ylimMin.name = 'min'
                ylimMax = DF.groupby(level=0,axis=1).max().max(axis=0)
                ylimMax.name = 'max'
                ylimPlot = pd.concat([ylimMin,ylimMax],axis=1)

            backend = mpl.get_backend()
            self.DFM.P.use('Agg')
            indices = list(DF.columns.names)
            indices.remove('histName')
            # DFs = np.array_split(DF,nc,axis=1)
            DFs = self.DFM.splitBy(DF,nc,indices,axis=1)
            nc = min(nc,len(DFs))
            variables = [(DF,saveName,saveLoc,ylimPlot,plotType,i) for i,DF in enumerate(DFs)]  # need to implement parallel version of **line2Dkwargs
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._plotHistoryDF,variables)
            result.wait()
            DFs = result.get()
            pool.close()
            self.DFM.P.use(backend)
            
        else:
            self._plotHistoryDF(DF,saveName=saveName,saveLoc=saveLoc,ylim=ylim,plotType=plotType,fig=1,**line2Dkwargs)
        executionTime = time.time()-startTime
        print('Done in %0.3f seconds'%executionTime)
        return 0
    
    def _plotHistoryDF(self,DF,saveName=None,saveLoc=None,ylim=None,plotType='single',fig=1,**line2Dkwargs):
        levels = list(DF.columns.names)
        histNames = DF.columns.get_level_values('histName').unique()
        if plotType == 'single':
            # make sure histName level is first
            if levels.index('histName') != 0:
                levels.remove('histName')
                levels = ['histName'] + levels
                DF = DF.reorder_levels(levels,axis=1).sort_index(axis=1)
            
            for histName in histNames:
                if isinstance(saveName,(str)): 
                    baseName = saveName + '_hist-%s'%histName
                else:
                    baseName = histName
                
                DFhist = DF[histName]
                sweepVars = list(DFhist.columns.names)
                if isinstance(ylim,(tuple, list)):
                    ylimPlot = ylim
                if isinstance(ylim,pd.core.frame.DataFrame):
                    ylimPlot = ylim.loc[histName].to_list()
                else:
                    ylimPlot = (DFhist.min(axis=None),DFhist.max(axis=None))
                    
                for i in range(len(DFhist.columns)):
                    DFplot = DFhist.iloc[:,i]
                    sweepVals = DFplot.name
                    baseNameDict = dict(zip(sweepVars, sweepVals))
                    saveTag = self.genBaseName(baseNameDict)
                    DFplot.name = histName
                    fig,ax = self.DFM.plot1D(DFplot)
                    ax.set(ylim=ylimPlot,**line2Dkwargs)
                    saveNamePlot = baseName + '_' + saveTag
                    if fig: fig.savefig(saveLoc + saveNamePlot + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
        else:
            # ensure histName level is last
            if levels.index('histName') != (len(levels)-1):
                levels.remove('histName')
                levels =  levels + ['histName']
                DF = DF.reorder_levels(levels,axis=1).sort_index(axis=1)
            if isinstance(saveName,(str)): 
                baseName = saveName
            else:
                baseName = histNames[0]
            sweepVars = list(DF.columns.names)
            sweepVars.remove('histName')
            if isinstance(ylim,(tuple, list)):
                ylimPlot = ylim
            elif isinstance(ylim,pd.core.frame.DataFrame):
                ylimPlot = (ylim.min(axis=None),ylim.max(axis=None))
            else:
                ylimPlot = (DF.min(axis=None),DF.max(axis=None))
            
            
            for sweepVals in DF.columns.droplevel('histName'):
                if not isinstance(sweepVals, (list,tuple)):
                    baseNameDict = dict(zip(sweepVars, [sweepVals]))
                else:
                    baseNameDict = dict(zip(sweepVars, sweepVals))
                saveTag = self.genBaseName(baseNameDict)
                fig,ax = self.DFM.plot1D(DF[sweepVals])
                ax.set(ylim=ylimPlot,**line2Dkwargs)
                saveNamePlot = baseName + '_' + saveTag
                if fig: fig.savefig(saveLoc + saveNamePlot + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
    
                
        return 0
        
    def plotHistory(self,histName,saveLoc=None,baseName=None,sweepVars=None):
        if saveLoc==None: saveLoc=self.resDir
        if type(baseName)==type(None):
            baseName = histName
        self.P.use('agg')
        
        for sweepDir in self.sweepDirs:
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            if sweepVars is None:
                saveTag = self.genBaseName(sweepDir,depth=self.baseNameDepth)
            elif type(sweepVars) is list:
                sweepVarsDict = DD.getScalerVars(sweepVars)
                saveTag = self.genBaseName(sweepVars,depth=self.baseNameDepth)
            saveName = baseName + '_' + saveTag
            DD.plotHistory(histName,saveLoc=saveLoc,saveName=saveName,fig=1)
        self.P.use()
        return
    
    def plotRelevant(self,saveLoc=None,freq=False,ow=False,sweepVars=None,nc=1):
        if saveLoc==None: saveLoc=self.resDir
        for sweepDir in self.sweepDirs:
            sweepDir = os.path.join(sweepDir,'')
            print('PlotRelevant Processing: %s'%(self.baseDir + sweepDir))
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            if sweepVars is None:
                baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
            elif type(sweepVars) is list:
                sweepVarsDict = DD.getScalerVars(sweepVars)
                numDecimals = 3
                sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
                baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
            elif type(sweepVars) is dict:
                numDecimals = list(sweepVars.values())
                sweepVars = list(sweepVars.keys())
                sweepVarsDict = DD.getScalerVars(sweepVars)
                sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
                baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
            DD.plotRelevant(saveLoc=saveLoc,saveTag=baseName,freq=freq,ow=ow,nc=nc)
            #DD.plotSpectrogram(histName=None,win=25e-9,saveLoc=saveLoc,saveTag=baseName)
            
    def _plotRelevantHistory(self,sweepDir,saveLoc=None,freq=None,ow=False,sweepVars=None,fig=1): 
        sweepDir = os.path.join(sweepDir,'')
        # print('sweep deletion debug: ow=%s'%ow)
        DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
        if sweepVars is None:
            baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
        elif type(sweepVars) is list:
            sweepVarsDict = DD.getScalerVars(sweepVars)
            numDecimals = 3
            sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
            baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
        elif type(sweepVars) is dict:
            numDecimals = list(sweepVars.values())
            sweepVars = list(sweepVars.keys())
            sweepVarsDict = DD.getScalerVars(sweepVars)
            sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
            baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
        DD.plotRelevantHistories(saveLoc=saveLoc,saveTag=baseName,freq=freq,ow=ow,fig=fig)
        
    
    def plotRelevantHistories(self,sweepDirs=None,saveLoc=None,freq='all',ow=False,sweepVars=None,nc=1):
        if sweepDirs==None: sweepDirs=self.sweepDirs
        if saveLoc==None: saveLoc=self.resDir
        sweepDirs = [sweepDir.replace(self.baseDir,'') for sweepDir in sweepDirs]
        # print(saveLoc)
        # nc=1 # parallel plotting has formatting errors, can't use for now.
        nc = min(nc,len(sweepDirs[1:]))
        print("Plotting Relevant Histories with %i Cores ..."%(nc),end=' ')
        startTime = time.time()
        if nc>1:
            
            # run the first sweepDir to overwrite properly, then parallel
            self._plotRelevantHistory(sweepDirs[0],saveLoc=saveLoc,freq=freq,ow=ow,sweepVars=sweepVars)
            ow=False
            variables = []
            for i,sweepDir in enumerate(sweepDirs[1:]):
                variables = variables + [(sweepDir,saveLoc,freq,ow,sweepVars,i)]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._plotRelevantHistory,variables)
            result.wait() # no return variable
            #tupleList = result.get()
            #DFList,varDictList = list(zip(*tupleList))
            pool.close()
            
        else:
            for i,sweepDir in enumerate(sweepDirs):
                if i == 0:  ow = ow
                else:  ow = False
                # print("  plotRelevantHistories Processing: '%s' ..."%(sweepDir),end=' ')
                singleStartTime = time.time()
                self._plotRelevantHistory(sweepDir,saveLoc=saveLoc,freq=freq,ow=ow,sweepVars=sweepVars)
                executionTime = (time.time() - singleStartTime)/60.
                # print(' Done in %.2f minutes'%(executionTime))
        
        executionTime = (time.time() - startTime)/60.
        print('Done in %.2f minutes'%(executionTime))
    
    def plotCycloidData(self,partTypes = ['electronsT'],bins=[100,150],sweepDirs=None,saveLoc=None,freq=False,nc=1):
        if sweepDirs==None: sweepDirs=self.sweepDir
        if saveLoc==None: saveLoc=self.resDir
        sweepDirs = [sweepDir.replace(self.baseDir,'') for sweepDir in sweepDirs]
        for i,sweepDir in enumerate(sweepDirs):
            baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
            sweepDir = os.path.join(sweepDir,'')
            print("plotCycloidData Processing: '%s'"%(sweepDir))
            # startTime = time.time()
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            DD.plotCycloidData(partTypes=partTypes,bins=bins,saveLoc=saveLoc,saveTag=baseName,freq=freq,nc=nc)
            progress = (i+1)/len(self.sweepDirs)*100
            # executionTime = (time.time() - startTime)/60.
            print('Sweep %5.1f%% Complete\n'%(progress))
    
    def _plotFreqSpokes(self,sweepDir,saveLoc=None,sweepVars=None,fig=1): 
        if saveLoc==None: saveLoc=self.resDir
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        
        if sweepVars is None:
            baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
        elif type(sweepVars) is list:
            sweepVarsDict = DD.getScalerVars(sweepVars)
            numDecimals = 3
            sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
            baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
        elif type(sweepVars) is dict:
            numDecimals = list(sweepVars.values())
            sweepVarsKeys = list(sweepVars.keys())
            sweepVarsDict = DD.getScalerVars(sweepVarsKeys)
            sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
            baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
        
        DD.plotFreqSpokes(saveLoc=saveLoc,saveTag=baseName,fig=fig)
    
    
    def plotFreqSpokes(self,sweepDirs=None,saveLoc=None,sweepVars=None,nc=1):        
        if sweepDirs==None: sweepDirs=self.sweepDirs
        if saveLoc==None: saveLoc=self.resDir
        nc = min(nc,len(sweepDirs))
        self.P.use('Agg')
        if nc > 1:
            variables = []
            for i,sweepDir in enumerate(self.sweepDirs):
                variables = variables + [(sweepDir,saveLoc,sweepVars,i)]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._plotFreqSpokes,variables)
            result.wait()
            pool.close()
        else: 
            for i,sweepDir in enumerate(sweepDirs):
                self._plotFreqSpokes(sweepDir,saveLoc=saveLoc,sweepVars=sweepVars,fig=1)
        self.P.use()
        
    def generateSummary(self,sweepDir,varList=[],ow=False,resDir=None):
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        DF = DD.generateSummary(varList=varList,ow=ow,resDir=resDir)
        DD.saveSummary()
        return 0
    
    def generateSummaries(self,varList=[],ow=False,nc=1):
        print("Generating Summaries with %i core(s): '%s'..."%(nc,self.baseDir))
        resDir=None
        nc = min(nc,len(self.sweepDirs))
        if nc > 1:
            variables = []
            for i,sweepDir in enumerate(self.sweepDirs):
                variables = variables + [(sweepDir,varList,ow,resDir)]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self.generateSummary,variables)
            result.wait()
            pool.close()
        else:
            loopCount = 0
            for sweepDir in self.sweepDirs:
                self.generateSummary(sweepDir,varList=varList,ow=ow,resDir=resDir)
                loopCount = loopCount + 1
                if loopCount%1 == 0:
                    print('\r  Processed: %d directories'%loopCount,end='')
        
        print('  Done \nSummaries Generated')
    
    def plotRelevantParticles(self,partTypes=None,steps='all',sweepDirs=None,saveLoc=None,bins=50,cutoffWeight=0.01,freq=False,ow=False,plotLockIn=False,sweepVars=None,nc=1):
        if sweepDirs==None: sweepDirs=self.sweepDirs
        if saveLoc==None: saveLoc=self.resDir
        sweepDirs = [sweepDir.replace(self.baseDir,'') for sweepDir in sweepDirs]
        
        for i,sweepDir in enumerate(sweepDirs):
            if i == 0:  ow=ow
            else:  ow=False
            
            sweepDir = os.path.join(sweepDir,'')
            print("plotRelevantParticles Processing: ./'%s'"%(sweepDir))
            #startTime = time.time()
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            if sweepVars is None:
                baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
            elif type(sweepVars) is list:
                sweepVarsDict = DD.getScalerVars(sweepVars)
                numDecimals = 3
                sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
                baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
            elif type(sweepVars) is dict:
                numDecimals = list(sweepVars.values())
                sweepVarsKeys = list(sweepVars.keys())
                sweepVarsDict = DD.getScalerVars(sweepVarsKeys)
                sweepVarsDict = DD.strDict(sweepVarsDict,numDecimals=numDecimals)
                baseName = self.genBaseName(sweepVarsDict,depth=self.baseNameDepth)
            
            
            DD.plotRelevantParticles(partTypes=partTypes,steps=steps,saveLoc=saveLoc,saveTag=baseName,bins=bins,cutoffWeight=cutoffWeight,freq=freq,ow=ow,plotLockIn=plotLockIn,nc=nc)
            progress = (i+1)/len(sweepDirs)*100
            #executionTime = (time.time() - startTime)/60.
            print('Sweep %5.1f%% Complete\n'%(progress))
            
    def plotSpectrograms(self,histName,sweepDirs=None,saveLoc=None,win=None):
        if sweepDirs==None: sweepDirs=self.sweepDir
        if saveLoc==None: saveLoc=self.resDir
        sweepDirs = [sweepDir.replace(self.baseDir,'') for sweepDir in sweepDirs]
        for sweepDir in sweepDirs:
            baseName = self.genBaseName(sweepDir,depth=self.baseNameDepth)
            sweepDir = os.path.join(sweepDir,'')
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            DD.plotSpectrogram(histName=histName,win=win,saveLoc=saveLoc,saveTag=baseName)
    
    def plotRelevantFields(self,fieldTypes=None,sweepDirs=None,saveLoc=None,freq=False,polar=False,nc=1):
        if sweepDirs==None: sweepDirs=self.sweepDir
        if saveLoc==None: saveLoc=self.resDir
        sweepDirs = [sweepDir.replace(self.baseDir,'') for sweepDir in sweepDirs]
        for i,sweepDir in enumerate(sweepDirs):
            # if i == 0:  ow=ow
            # else:  ow=False
            baseName = self.genBaseName(sweepDir)
            sweepDir = os.path.join(sweepDir,'')
            print("plotRelevantFields Processing: '%s'"%(self.baseDir + sweepDir))
            DD = dataDir.DataDir(self.baseDir + sweepDir,relHAPlots=self.relHAPlots,relEAPlots=self.relEAPlots,visit=self.visit)
            DD.plotRelevantFields(fieldTypes=fieldTypes,saveLoc=saveLoc,saveTag=baseName,freq=freq,polar=polar,nc=1)
           
    
    
    # def plotDrData(self,partTypes=['electronsT'],tagRatio=.1,saveLoc=None,nc=1):
    #     if type(saveLoc)==type(None): saveLoc=self.resDir
    #     if not type(partTypes) is list: partTypes = [partTypes]
    #     self.P.use('agg')
    #     for sweepDir in self.sweepDirs:
    #         baseName = self.genBaseName(sweepDir)
    #         DD = dataDir.DataDir(self.baseDir + sweepDir)
    #         for partType in partTypes:
    #             DF = DD.Parts.readAllAsDF(partType,steps=None,relData=['x','y','ux','uy','tag'],tagRatio=tagRatio,nc=nc)
    #             DF = DD.calcCycloidData(DF,xy=['x','y'],uxy=['ux','uy'])
    #             fig,ax,plot,cbar = DD.plotDrData(DF,bins=50,saveLoc=saveLoc,partType=partType,saveTag=baseName)
    #     self.P.use()
    
    def _plotDr(self,sweepDir,partTypes=['electronsT'],tagRatio=0.2,xy=['x','y'],uxy=['ux','uy'],bins=50,saveLoc=None,nc=1):
        baseName = self.genBaseName(sweepDir)
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        for partType in partTypes:
            fig,ax,plot,cbar = DD.plotDr(partType=partType,tagRatio=tagRatio,xy=xy,uxy=uxy,bins=bins,saveLoc=saveLoc,saveTag=baseName,nc=nc)
    
    
    
    def plotDr(self,partTypes=['electronsT'],tagRatio=0.2,xy=['x','y'],uxy=['ux','uy'],bins=50,saveLoc=None,nc=1):
        if type(saveLoc)==type(None): saveLoc=self.resDir
        if not type(partTypes) is list: partTypes = [partTypes]
        
        self.P.use('agg')
        if nc > 1:
            # run the first sweepDir to overwrite properly, then parallel
            variables = []
            for i,sweepDir in enumerate(self.sweepDirs):
                variables = variables + [(sweepDir,partTypes,tagRatio,xy,uxy,bins,saveLoc,1)]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._plotDr,variables)
            result.wait() # no return variable
            #tupleList = result.get()
            #DFList,varDictList = list(zip(*tupleList))
            pool.close()
            
        else:
            for sweepDir in self.sweepDirs:
                self._plotDr(partTypes=partTypes,tagRatio=tagRatio,xy=xy,uxy=uxy,bins=bins,saveLoc=saveLoc,nc=1)
            
        self.P.use()
        
    def _loadDias(self,diaList, diaType, sweepDir,relVars=None):
        if not type(relVars) is list:
            relVars = [relVars]
        N = len(diaList)
        sweepDir = os.path.join(sweepDir,'')
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        loaderDict = {diaType:{}}
        DF = DD.applyMany(diaList,loaderDict) 
        sweepDir = os.path.normpath(sweepDir)
        if type(relVars[0]) == type(None):
            varDict = self.getVarsFromDir(sweepDir,dtype='Dict',Nrepeat=N)
        else:
           varDict = DD.getScalerVars(relVars)
           for key,value in varDict.items():
               varDict[key] = [value]*N
               
        varDict['diagnostic'] = diaList
        return DF, varDict
        
    def loadDias(self,diaList, diaType, sweepDirs=None,relVars=None,nc=1):
        if type(sweepDirs)==type(None): sweepDirs = self.sweepDirs
        if not type(diaList) is list: diaList = [diaList]
        
        N = len(diaList)
        if nc>1:
            variables = []
            for i,sweepDir in enumerate(self.sweepDirs):
                variables = variables + [(diaList,diaType,sweepDir,relVars)]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self._loadDias,variables)
            result.wait()
            tupleList = result.get()
            DFList,varDictList = list(zip(*tupleList))
            pool.close()
        else:
            DFList = []
            varDictList = []
            for sweepDir in sweepDirs:
                DF, varDict = self._loadDias(diaList, diaType, sweepDir,relVars)
                DFList = DFList + [DF]
                varDictList = varDictList + [varDict]

        DF = pd.concat(DFList,axis=1)
        Dict = self.combineDicts(varDictList)
        mi = pd.MultiIndex.from_frame(pd.DataFrame(Dict))
        
        DF.columns = mi
        DF = DF.stack(list(Dict.keys())[:-1])
        return DF
    
    def getScalerSweepData(self,diaList,methodDict={'self.DFM.reduce':{'iName':'t','method':'mean','theRange':[0.90,1.0]}},sweepDirs=None):
        if not type(diaList) is list: diaList = [diaList]
        if type(sweepDirs)==type(None): sweepDirs = self.sweepDirs
        
        DF = self.loadDias(diaList, 'self.Hists.readManyAsOneDF')
        #DF = self.DFM.reduce(DF,'t',method='mean',theRange=theRange)
        DF = self.apply(DF,methodDict)
        return DF
    
    def plotScalerSweep(self,diaList,methodDict={'self.DFM.reduce':{'iName':'t','method':'mean','theRange':[0.75,1.0]}},saveLoc=None,sweepDirs=None):
        if type(saveLoc)==type(None): saveLoc=self.resDir
        saveLoc=saveLoc + 'sweep/'
        if not os.path.exists(saveLoc):
            os.makedirs(saveLoc) 
        DF = self.getScalerSweepData(diaList=diaList,methodDict=methodDict,sweepDirs=sweepDirs)
        fig,ax = self.DFM.plot1D(DF)
        if fig: fig.savefig(saveLoc + ''.join(diaList) + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
        return fig,ax
    
    def get2DScalerSweepData(self,varRead,varCtrls=None, dataDirList=None, theRange = (0.50, 1.0),nc=1):
        DF = self.loadDias(varRead,diaType='self.Hists.readManyAsOneDF',nc=nc)
        DF = self.DFM.reduce(DF,'t',method='mean',theRange=theRange)
        return DF
    
    def plot2DScalerSweep(self,varRead,varCtrls=None, dataDirList=None, theRange = (0.50, 1.0),nc=1): 
        DF = self.get2DScalerSweepData(varRead,varCtrls=varCtrls, dataDirList=dataDirList, theRange=(0.50, 1.0),nc=nc)
        fig,ax,plot,cbar = self.DFM.tricontourf(DF,fig=None,figsize=(12, 5),clear=True)
        return fig,ax,plot,cbar
    
    
    def _processSweepDir(self,sweepDir,histNamesP=None,histNamesV=None,histNamesRho=None,histNamesE=None,relVars=None,linkPreface='file://' ):
        if not type(relVars) is list:
            relVars = [relVars]
        # histNames=['Pout','Vout','RhoCircleR05']
        theRange = [0.75,1.0]
        
        print('processing %s'% sweepDir)
        sweepDir = os.path.join(sweepDir,'')
        
        # sweepVars = sweepVars.stack().reset_index(0,drop=True)
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        tBuff = 10e-9
        # detect startup to get the longest steady state signal possible
        histName = 'Pout'
        DF = DD.Hists.readAsDF(histName)
        tStart = DD.DFM.getStartup(DF,debug=False) + tBuff
        tend = DD.Hists.tend
        if tStart>tend*0.9:
            tStart = tend*0.9
        theRange = np.array([tStart/tend,1])


        if type(relVars[0]) == type(None):
            sweepVars = self.getVarsFromDir(sweepDir,dtype='DF')
        else:
            sweepVars = DD.getScalerVars(relVars,theRange=theRange,dtype='DF')
            # sweepVars = pd.DataFrame(sweepVars,index=[0])
        
        stable = DD.checkStability(noiseLevel=-35,debug=False)
        stable = pd.DataFrame([[stable]],columns=['stable'])
        
        # interesting way to add two levels of variables to index below
        # DF[sweepVars.index]=sweepVars
        # DF = DF.set_index(list(sweepVars.index),append=True)
        # DFList = DFList + [DF]
        phiCol = 'phi'
        tCol = 't'
        DFList = [sweepVars,stable]
        check,histNamesRho = DD.Hists.checkDataset(histNamesRho,output=True)
        if (not type(histNamesRho) == type(None)) and check: 
            if not type(histNamesRho) == list: histNamesRho = [histNamesRho]
            rho = DD.Hists.readAsDF(histNamesRho[0])
            # get spoke phase in rotating frame of reference
            rho = rho[[phiCol]+[histNamesRho[0]]].reset_index(['point','v'],drop = True)
            rho = DD.rotRefFrame(rho)
            rho[phiCol] = (rho[phiCol]%(2*np.pi))
            rho = rho.set_index(phiCol,append=True).sort_index(level=[phiCol,tCol])
            rho = DD.DFM.reduce(rho,'t',method='mean',theRange=theRange)*-1.
            nMode = DD.PreVars.read(['NMODE'])['NMODE']
            period = 2*np.pi/nMode
            # self.DFM.plot1D(rho, fig=1)
            phase = self.DFM.getPhase(rho,period=period,hRatio=0.4,pRatio=0.3)
            #phase = (phase + np.pi)%(2*np.pi)-np.pi  # to convert to??? -pi to pi
            #phase = phase * period/2/np.pi # to convert to first spoke position
            # DFList = DFList + [pd.DataFrame([[phase]],columns=['spokePhase'])]
            phase.columns = ['spokePhase']
            DFList = DFList + [phase]
            
        check,histNamesE = DD.Hists.checkDataset(histNamesE,output=True)
        if (not type(histNamesE) == type(None)) and check: 
            if not type(histNamesE) == list: histNamesE = [histNamesE]
            E = DD.Hists.readAsDF(histNamesE[0])
            
            # get Ephi phase in rotating frame of reference
            E = E[['phi']+histNamesE].reset_index(['point'],drop = True).set_index('phi',append=True).reorder_levels(['t','phi','v'])
            E = self.DFM.cart2CylVector(E,vecIndex='v',phiIndex='phi')
            E = DD.DFM.reduce(E,iName='v',method='value',value=1)
            E = E.reset_index('phi')
            E = DD.rotRefFrame(E)
            E[phiCol] = (E[phiCol]%(2*np.pi))
            E = E.set_index(phiCol,append=True).sort_index(level=[phiCol,tCol])
            
            E = DD.DFM.reduce(E,'t',method='mean',theRange=theRange)
            nMode = DD.PreVars.read(['NMODE'])['NMODE']
            period = 2*np.pi/nMode
            # self.DFM.plot1D(rho, fig=1)
            phase = self.DFM.getPhase(E,period=period,hRatio=0.4,pRatio=0.3)
            #phase = (phase + np.pi)%(2*np.pi)-np.pi  # to convert to??? -pi to pi
            #phase = phase * period/2/np.pi # to convert to first spoke position
            # DFList = DFList + [pd.DataFrame([[phase]],columns=['spokePhase'])]
            phase.columns = ['EPhase']
            DFList = DFList + [phase]
        
        check,histNamesP = DD.Hists.checkDataset(histNamesP,output=True)
        if (not type(histNamesP) == type(None)) and check: 
            if not type(histNamesP) == list: histNamesP = [histNamesP]
            DF = DD.Hists.readAsDF(histNamesP[0])
            
            hRatio=0.4
            pRatio=0.4
            startup = self.DFM.getStartup(DF)
            
            try: Tbeat = self.DFM.getBeatPeriod(DF,hRatio=None,pRatio=0.1)
            except: Tbeat = np.nan
            DFList = DFList + [pd.DataFrame([[startup,Tbeat]],columns=['startup','Tbeat'])]
            
            DF = self.DFM.reduce(DF,'t',method='mean',theRange=theRange)
            DF = DF.to_frame().T
            DFList = DFList + [DF]
            
        check,histNamesV = DD.Hists.checkDataset(histNamesV,output=True)
        if (not type(histNamesV) == type(None)) and check: 
            if not type(histNamesV) == list: histNamesV = [histNamesV]
        
            V = DD.Hists.readAsDF(histNamesV[0])
            # stable,freqPeaks = self.DFM.checkStability(V,theRange=theRange,pRatio=0.04)
            
            # tStart = self.DFM.getStartup(V,method='bandpass')   # might not sork because its Vout, not Pout
            fftRange = theRange
            Vfft = DD.DFM.FFT(V,theRange=fftRange)
            Vfft = DD.DFM.FFTamplitude(Vfft)
            Vfft = 20*np.log10(Vfft)
            
            freqPeaks,props = self.DFM.findPks(Vfft,maxPks=10,pRatio=0.05,height=-50)
            
            # get beat frequency using FFT peaks
            freqPeaks = freqPeaks.sort_values('abs(FFT(%s))'%histNamesV[0],ascending=False)
            # get beat frequency using FFT peaks
            if len(freqPeaks)>1: Fbeat = abs(freqPeaks.index[1]-freqPeaks.index[0])/1e9
            else: Fbeat=np.nan
            
            # get phase of output
            period = 1./DD.PreVars.read(['FREQ'])['FREQ']
            V = self.DFM.cutRange(V,theRange=theRange)
            phase = self.DFM.getPhase(V,period=period,hRatio=0.4,pRatio=0.3)
            
            DFList = DFList + [pd.DataFrame([[Fbeat,phase.iloc[0][0]]],columns=['Fbeat','VoutPhase'])]
            

        # add directory
        linkPreface = 'file://'
        DF = pd.DataFrame([[linkPreface + self.baseDir + sweepDir]],columns=['directory'])
        DFList = DFList + [DF]
        # DF1 = pd.concat([DF,sweepVars],axis=1)
        #DF1 = pd.DataFrame([[phase,startup,stable,Fbeat,Tbeat]],columns=['phase','startup','stable','Fbeat','Tbeat'])
        DF = pd.concat(DFList,axis=1)
        return DF
    
    def processSweep(self,histNamesP=None,histNamesV=None,histNamesRho=None,histNamesE=None,relVars=None,nc=1,ow=False):
        # read power, check stability,check beat frequency, etc
        linkPreface = 'file://' 
        if not type(relVars) is list:
            relVars = [relVars]
        saveName = self.sweepDataSaveName
        saveLoc = self.sweepDataSaveLoc
        sweepDirs = self.sweepDirs
        sweepData = glob.glob(self.baseDir+saveName + '.h5')
        processDirs = True
        DFList = []
        print('Processing Sweep Directory: %s'%self.baseDir)
        if (len(sweepData) == 1) and not ow:
            print("Reading from datafile '%s' found in %s..."%(saveName,self.baseDir))
            DF = pd.read_hdf(sweepData[0])
            processDirs = False
        elif (len(sweepData) == 1) and (ow == 'append'):
            print("Reading from datafile '%s' found in %s and appending..."%(saveName,self.baseDir))
            DF = pd.read_hdf(sweepData[0]).reset_index(drop=True)
            #DF = DF.drop(labels=[0.145],level=0).reset_index()
            
            iRemove = []
            processedDirs = DF['directory'].to_list()
            for i,processedDir in enumerate(processedDirs):
                if os.path.exists(processedDir.replace(linkPreface,'')):
                    sweepDirs.remove(processedDir.replace(linkPreface+self.baseDir,'').strip('/'))
                else:
                    iRemove = iRemove + [i]
            if len(iRemove)>0:
                DF = DF.drop(iRemove).reset_index(drop=True)     
            DFList = [DF]
        nc=1  # parallel implementation doesnt work....    
        if processDirs:
            if type(relVars[0]) is None:
                relVars = self.getVarsFromDir(self.sweepDirs[0],dtype='List')[0]
            else:
                relVars = relVars
            if nc <= 1:
                for sweepDir in sweepDirs:
                    # try:
                        DF = self._processSweepDir(sweepDir,histNamesP=histNamesP,histNamesV=histNamesV,histNamesRho=histNamesRho,histNamesE=histNamesE,relVars=relVars,linkPreface=linkPreface)
                        DFList = DFList + [DF]
                    # except:
                        # print('Error reading sweep directory: %s'%sweepDir)
                    # print('stepping through dirs...')
            else:
                variables = []
                for i,sweepDir in enumerate(sweepDirs):
                    variables = variables + [(sweepDir,histNamesP,histNamesV,histNamesRho,histNamesE,relVars,linkPreface)]
                pool = Pool(processes=nc)
                result = pool.starmap_async(self._processSweepDir,variables)
                result.wait()
                DFList = DFList + result.get()
                # DFList,varDictList = list(zip(*tupleList))
                pool.close()
                
            if len(DFList) > 0: DF = pd.concat(DFList)
            # DF = DF.set_index(sweepVars)
            DF = DF.reset_index(drop=True)
            
              
        # DF = DF.drop('directory',axis='columns')
        print('Finished Processing Sweep Directory')
        return DF
    
    def plot2DSweeps(self,DF,vars2D = ['BSTATIC','VDC'],histNamesP=None,histNamesV=None,histNamesRho=None,histNamesE=None,saveLoc=None):
        # will have to step through none 2D vars, plot 2D sweeps, and properly name the images
        if type(saveLoc)==type(None): saveLoc=self.resDir
        iNames = list(DF.index.names)
        for var2D in vars2D: 
            iNames.remove(var2D)
        stepVars = copy.deepcopy(iNames)
        NStepVars = len(stepVars)
        iNames = iNames + vars2D
        DF = DF.reorder_levels(iNames)
        stepValues = DF.reset_index(vars2D).index.unique()
        for i,stepValue in enumerate(stepValues):
            saveIdentifier = self.genBaseName(stepValues.to_frame(index=False).iloc[i].to_dict())
            self.plot2DSweep(DF.loc[stepValue],histNamesP=histNamesP,histNamesV=histNamesV,histNamesRho=histNamesRho,histNamesE=histNamesE,saveLoc=saveLoc,saveIdentifier=saveIdentifier)
        
        pass
    
    def plot2DSweep(self,DF,histNamesP=None,histNamesV=None,histNamesRho=None,histNamesE=None,saveLoc=None,saveIdentifier=None):
        if not type(histNamesP) is list: histNamesP =[histNamesP]
        if not type(histNamesV) is list: histNamesV =[histNamesV]
        if not type(histNamesRho) is list: histNamesRho =[histNamesRho]
        if not type(histNamesE) is list: histNamesE =[histNamesE]
        if type(saveLoc)==type(None): saveLoc=self.resDir
        if type(saveIdentifier)==type(None): saveIdentifier=''
        else:saveIdentifier='_' + saveIdentifier
        saveLoc=saveLoc + 'sweep/'
        if not os.path.exists(saveLoc):
            os.makedirs(saveLoc) 
        self.P.use('Agg')    
        # pcolor
        DF1 = copy.deepcopy(DF)
        DF1 = self.DFM.makeUniformDF(DF1,interpolate=False)
        DF = self.DFM.makeUniformDF(DF)
        stableVar = 'stable'
        plotVar = histNamesP[0]
        oneD = '1D'
        if stableVar in DF.columns: DF.loc[~DF[stableVar].astype('bool'),plotVar] = np.nan
        figNum = 1
        if plotVar in DF.columns:
            
            fig,ax,plot0,cbar0 = self.DFM.pcolor(DF[plotVar],fig=figNum,figsize=(10, 8),clear=True)
            if False: # 'stable' in DF.columns:
                fig,ax,plot1,cbar1 = self.DFM.pcolor(DF[stableVar].replace(True,np.nan),fig=figNum,figsize=(10, 8),clear=False,cmap='Reds')
                cbar0.remove()
                cbar1.remove()
                fig.colorbar(plot0,ax=ax)
                fig.canvas.draw()
            
            saveName = plotVar + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            fig,ax = self.DFM.plot1Ds(DF[plotVar],fig=figNum)
            saveName = plotVar + oneD + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            
            #figNum = figNum + 1
            plotVar = 'startup'
            fig,ax,plot,cbar = self.DFM.pcolor(DF[plotVar],fig=figNum,figsize=(10, 8),clear=True)
            saveName = plotVar + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            fig,ax = self.DFM.plot1Ds(DF[plotVar],fig=figNum)
            saveName = plotVar + oneD + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            #figNum = figNum + 1
        # contour
        # fig,ax,plot0,cbar0 = self.DFM.tricontourf(DF['Pout'],fig=1,figsize=(10, 8),clear=True)
        # fig,ax,plot1,cbar1 = self.DFM.tricontourf(DF['stable'].replace(True,np.nan),fig=1,figsize=(10, 8),clear=False,cmap='Reds')
        
        # if histNamesRho[0] in DF.columns:
        plotVar = 'spokePhase'
        if plotVar in DF.columns:
            if stableVar in DF.columns: DF.loc[~DF[stableVar].astype('bool'),plotVar] = np.nan

            fig,ax,plot0,cbar0 = self.DFM.pcolor(DF[plotVar],fig=figNum,figsize=(10, 8),clear=True)
            if False: #'stable' in DF.columns:
                fig,ax,plot1,cbar1 = self.DFM.pcolor(DF[stableVar].replace(True,np.nan),fig=figNum,figsize=(10, 8),clear=False,cmap='Reds')
                cbar0.remove()
                cbar1.remove()
                fig.colorbar(plot0,ax=ax)
                fig.canvas.draw()
            saveName = plotVar + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            fig,ax = self.DFM.plot1Ds(DF[plotVar],fig=figNum)
            saveName = plotVar + oneD + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            #figNum = figNum + 1
        
        plotVar = 'EPhase'
        if plotVar in DF.columns:
            if stableVar in DF.columns: DF.loc[~DF[stableVar].astype('bool'),plotVar] = np.nan

            fig,ax,plot0,cbar0 = self.DFM.pcolor(DF[plotVar],fig=figNum,figsize=(10, 8),clear=True)
            if False: #'stable' in DF.columns:
                fig,ax,plot1,cbar1 = self.DFM.pcolor(DF[stableVar].replace(True,np.nan),fig=figNum,figsize=(10, 8),clear=False,cmap='Reds')
                cbar0.remove()
                cbar1.remove()
                fig.colorbar(plot0,ax=ax)
                fig.canvas.draw()
            saveName = plotVar + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            fig,ax = self.DFM.plot1Ds(DF[plotVar],fig=figNum)
            saveName = plotVar + oneD + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            #figNum = figNum + 1
        
        plotVar = 'Fbeat'
        if plotVar in DF.columns:
            saveName = plotVar + saveIdentifier
            fig,ax,plot0,cbar0 = self.DFM.pcolor(DF1[plotVar],fig=figNum,figsize=(10, 8),clear=True)
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            fig,ax = self.DFM.plot1Ds(DF[plotVar],fig=figNum)
            saveName = plotVar + oneD + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            #figNum = figNum + 1
        plotVar = 'Tbeat'
        if plotVar in DF.columns:
            saveName = plotVar + 'all' + saveIdentifier
            fig,ax,plot0,cbar0 = self.DFM.pcolor(DF[plotVar],fig=figNum,figsize=(10, 8),clear=True)
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            fig,ax = self.DFM.plot1Ds(DF[plotVar],fig=figNum)
            saveName = plotVar + 'all'  + oneD + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            #figNum = figNum + 1
            if stableVar in DF.columns: DF.loc[~DF[stableVar].astype('bool'),plotVar] = np.nan
            saveName = plotVar + 'stable' + saveIdentifier
            fig,ax,plot0,cbar0 = self.DFM.pcolor(DF[plotVar],fig=figNum,figsize=(10, 8),clear=True)
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            
            fig,ax = self.DFM.plot1Ds(DF[plotVar],fig=figNum)
            saveName = plotVar + 'stable'  + oneD + saveIdentifier
            if not type(fig) is type(None): fig.savefig(saveLoc + saveName + '.' + self.P.saveType, bbox_inches='tight', format=self.P.saveType)
            #figNum = figNum + 1 
            
        self.P.use()
        return fig,ax 
    
    def __get2DScalerSweepData(self,varRead,varCtrls, dataDirList=None, avgRange = (0.50, 1.0)):
        if self.debug: print('processing sweep: %s vs %s'%( varRead, varCtrls ))
        varX = np.array([])
        varY = np.array([])
        varZ = np.array([])
        varience = np.array([])
        for directory in dataDirList:
            DD = dataDir.DataDir(directory,self.relHAPlots)
            varZ = np.append(varZ,DD.getScalerVars(varRead, avgRange)[varRead])
            varX = np.append(varX,DD.getScalerVars(varCtrls[0], avgRange)[varCtrls[0]])
            varY = np.append(varY,DD.getScalerVars(varCtrls[1], avgRange)[varCtrls[1]])
            #varY = np.append(varY,DD.HA.scalerAvg(varCtrls[1], avgRange))
            #varience = np.append(varience,DD.HA.getVarience(varRead,n=300,varRange=avgRange))
        return (varX,varY,varZ)   #,varience
        
    def __plot2DScalerSweep(self,varRead,varCtrls, dataDirList=None, avgRange = (0.50, 1.0)):
        varX,varY,varZ = self.get2DScalerSweepData(varRead,varCtrls, dataDirList=dataDirList, avgRange = avgRange)
        
        f = interp2d(varX,varY,varZ,kind='linear')
        X=np.linspace(min(varX),max(varX),100)
        Y=np.linspace(min(varY),max(varY),100)
        Z = f(X,Y)
        fig = plt.imshow(Z,
           extent=[min(varX),max(varX),min(varY),max(varY)],
           origin="lower")
        
        return varX,varY,varZ
    
    def generateSummary(self,sweepDir,varList=[],ow=False,resDir=None):
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        DF = DD.generateSummary(varList=varList,ow=ow,resDir=resDir)
        DD.saveSummary()
        return 0
    
    def generateSummaries(self,varList=[],ow=False,nc=1):
        print("Generating Summaries with %i core(s): '%s'..."%(nc,self.baseDir))
        resDir=None
        nc = min(nc,len(self.sweepDirs))
        if nc > 1:
            variables = []
            for i,sweepDir in enumerate(self.sweepDirs):
                variables = variables + [(sweepDir,varList,ow,resDir)]
            pool = Pool(processes=nc)
            result = pool.starmap_async(self.generateSummary,variables)
            result.wait()
            pool.close()
        else:
            loopCount = 0
            for sweepDir in self.sweepDirs:
                self.generateSummary(sweepDir,varList=varList,ow=ow,resDir=resDir)
                loopCount = loopCount + 1
                if loopCount%1 == 0:
                    print('\r  Processed: %d directories'%loopCount,end='')
        
        print('  Done \nSummaries Generated')
    
    def cleanDirectory(self,sweepDir,relevantH5=None):
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        return DD.cleanDirectory(relevantH5=relevantH5)
        
    def cleanDirectories(self,relevantH5=None,nc=1):
        print("cleaning Directories with %i core(s): '%s'... "%(nc,self.baseDir))
        nc = min(nc,len(self.sweepDirs))
        if nc > 1:
            variables = []
            for sweepDir in self.sweepDirs:
                variables = variables + [(sweepDir,relevantH5)]
            
            pool = Pool(processes=nc)
            result = pool.starmap_async(self.cleanDirectory,variables)
            result.wait()
            huh = result.get()
            pool.close()
        else:
            loopCount = 0
            for sweepDir in self.sweepDirs:
                self.cleanDirectory(sweepDir,relevantH5)
                loopCount = loopCount + 1
                if loopCount%1 == 0:
                    print('\r  Processed: %d directories'%loopCount,end='')
        
        print('  Done \nDirectories Cleaned')
    
    def checkForParticleFile(self,sweepDir,partType='electronsT',relevantH5='_phi.t_'):
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        return DD.checkForParticleFile(partType=partType,relevantH5=relevantH5)
    
    def checkForParticleFiles(self,partType='electronsT',relevantH5='_phi.t_',nc=1):
        
        nc = min(nc,len(self.sweepDirs))
        print('Checking for Particle Files with %i Cores... '%nc,end='')
        startTime = time.time()
        if nc > 1:
            variables = []
            for sweepDir in self.sweepDirs:
                variables = variables + [(sweepDir,partType,relevantH5)]
            
            pool = Pool(processes=nc)
            result = pool.starmap_async(self.checkForParticleFile,variables)
            result.wait()
            exists = result.get()
            pool.close()
        else:
            exists = []
            for sweepDir in self.sweepDirs:
                exist = self.checkForParticleFile(sweepDir,partType,relevantH5)
                exists = exists + [exist]
        
        executionTime = (time.time() - startTime)/60.0
        print('Done in %0.2f minutes'%(executionTime))
        return exists
    
    def generateParticleFiles(self,partType='electronsT',relevantH5='_phi.t_',freq=True,nc=1):
        exists = SDD.checkForParticleFiles(partType=partType,relevantH5=relevantH5,nc=nc)
        processDirs = [sweepDir for exist,sweepDir in zip(exists,SDD.sweepDirs) if not exist]
        print('%i directories will be processed'%(len(processDirs)))
        for processDir in processDirs:
            print('Generating Particle File: %s'%processDir)
            DD = dataDir.DataDir(self.baseDir + processDir)
            DD.generateParticleFile(partType=partType,freq=freq,nc=nc)
        return 0
    
    def readSummary(self,sweepDir):
        DD = dataDir.DataDir(self.baseDir + sweepDir)
        DF = DD.readSummary()
        return DF
    
    def combineSummaries(self,saveLoc=None,saveName=None,nc=1):
        if type(saveLoc)==type(None): saveLoc=self.resDir
        if type(saveName)==type(None): saveName='dataSummary.csv'
        saveLoc = os.path.join(saveLoc,'')
        if not os.path.exists(saveLoc):
            os.makedirs(saveLoc)
        
        print("Combining Summaries with %i core(s): '%s'..."%(nc,self.baseDir))
        
        
        if nc > 1:
            pool = Pool(processes=nc)
            result = pool.map_async(self.readSummary,self.sweepDirs)
            result.wait()
            DFs = result.get()
            pool.close()
        else:
            loopCount = 0
            DFs = []
            for sweepDir in self.sweepDirs:
                DF = self.readSummary(sweepDir)
                DFs = DFs + [pd.DataFrame(DF)]
                loopCount = loopCount + 1
                if loopCount%50 == 0:
                    print('\rProcessed: %d directories'%loopCount,end='')
        DF = pd.concat(DFs)
        DF.to_csv(saveLoc+saveName)
        print('  Done \nSummary Saved: %s'%(saveLoc+saveName))
        return DF
            
    def genLookupDF(self,varList=None,saveLoc=None,saveName=None):
        if type(saveLoc)==type(None): saveLoc=self.baseDir
        if type(saveName)==type(None): saveName='dataLookup.xlsx'
        saveLoc = os.path.join(saveLoc,'')
        print('Generating Entries: %s'%(self.baseDir))
        print('varList = %s'%varList)
        DFlist = []
        loopCount = 0
        for root,dirs,files in os.walk(self.baseDir,followlinks=True):
            try: 
                DD = dataDir.DataDir(os.path.join(root,''))
                DF = DD.genLookupEntry(varList)
                DFlist = DFlist + [DF]
            except: pass
            loopCount = loopCount + 1
            if loopCount%50 == 0:
                print('\rProcessed: %d directories'%loopCount,end='')
                # print('##################\nProcessed: %d directories\n##################'%loopCount)
        DF = pd.concat(DFlist)
        #print(self.baseDir + 'dataLookup.xlsx')
        DF.to_excel(saveLoc+saveName) 
        
        print('  Done \nEntries Saved: %s'%(saveLoc+saveName))
        return DF
    
    def readDataLookup(self):
        if os.path.exists(self.dataLookupFile):
            DF = pd.read_excel(self.dataLookupFile)
        else: 
            raise Exception("Data lookup file '%s' does not exist"%self.dataLookupFile)
            DF = None
        return DF
        
    def findDataDirs(self,DF,criteria):
        """
        search the data directories for runs that meet a specific criteria and return the run locs. This will
        be used in conjunction with plotScalerSweep.
        criteria is a dict with the variable name as the key and the value is a list of two values: the low and the high
        {'var0':[100,100], 'var1':[50,55]}
        """
        
        DF = copy.copy(DF)
        for variable in list(criteria.keys()):
            if type(criteria[variable]) is not list: criteria[variable] = [criteria[variable],criteria[variable]]
            DF = DF[DF[variable]>=criteria[variable][0]]
            DF = DF[DF[variable]<=criteria[variable][1]]
            
        #DF.pop('Unnamed: 0')
        
        DF.to_excel(self.baseDir + 'dataLookup_filtered.xlsx') 
        
        return list(DF['runLoc'] )
        
        
if __name__ == "__main__":
    startTime = time.time()
    # folder = '/media***REMOVED******REMOVED***/Documents/CFA_data/2023/date-01.09.23/VSweep/PARTICLES-1/BSTATIC-0.140/' 
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/VBsweep/PRF_AVG-450e3/' 
    # # folder = '/home***REMOVED***Documents/fastData/CFAdata/VBsweep/'
    # SDD = SweepDataDir(folder)
    # histNames = ['Pout','Vout']

    # #histNames = ['Evane0']
    
    
    # # DF = SDD.loadDias(histNames, 'self.Hists.readManyAsOneDF',relVars=relVars,nc=12)
    # nc=16
    # DF = SDD.processSweep(histNamesP='Pout',histNamesV='Vout',histNamesRho='RhoCircleR05',histNamesE='EedgeCircleR050',sweepVars=sweepVars,relVars=relVars,nc=nc,ow=True)
    # # SDD.plot2DSweep(DF,histNamesP='Pout')
    # pd.set_option('expand_frame_repr', False)  # print DataFrames in the terminal without omission
    # print(DF)
    
    ######################
    #     test get rel vars
    ######################
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/VBsweep/PRF_AVG-450e3/' 
    # relVars = ['FREQ','VDC']
    # SDD = SweepDataDir(folder)
    # DF = SDD.getRelVars(relVars)
    # DF.loc[(DF['FREQ'] == 1.3e9) & (DF['VDC'] <= 94e3) & (DF['VDC'] >= 90e3)]
    
    ######################
    #     find and open 1D sweep directories
    ######################
    # # delayHours = 7
    # # delaySecs = delayHours*60*60
    # # print('Delay set: waiting %i hours before processing data...'%delayHours)
    # # sleep(delaySecs)
    
    
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/2023/feaEmitterTests/' 
    # # folder = '/home***REMOVED***Documents/fastData/CFAdata/2023/feaEmitterTests/feaEmitter-1/rEndHatEmit0-0.3/profile-sinePulse/' 
    # subDirs = list(list(zip(*os.walk(folder,followlinks=True)))[0])
    # subSubDirsOld = list(list(zip(*os.walk(folder,followlinks=True)))[1])
    # dirLen = 0
    # nc=12

    # partTypes=['electronsT','modElectronsT',['electronsT','modElectronsT']]
    # bins = [100,150,1]
    # cutoffWeight = 0.01
    # fieldTypes=['E']
    # steps = 'all'
    # ow=True
    # frameSkip = 1
    
    
    # subSubDirs = []
    # for subDir,subSubDir in zip(copy.copy(subDirs),subSubDirsOld):
    #     if ('processed' in subDir) or ('runScripts' in subDir):
    #         subDirs.remove(subDir)
    #     else:
    #         subSubDirs = subSubDirs + [subSubDir]
    #         dirLen = max(len(os.path.join(subDir,'').split('/')),dirLen)
    
    # for subDir,subSubDir in zip(copy.copy(subDirs),subSubDirs):
    #     # if len(os.path.join(subDir,'').split('/')) != (dirLen-1):
    #     if len(subSubDir) == 0:    
    #         subDirs.remove(subDir)
    #     else:
    #         folder = os.path.join(subDir,subSubDir[0])
    #         subSubSubDirs = [name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))]
    #         if len(subSubSubDirs) > 0:
    #             subDirs.remove(subDir)
                
            
    # #subDirs = ['/home***REMOVED***Documents/fastData/CFAdata/2023/feaEmitterTests/feaEmitter-1/rEndHatEmit0-0.3/profile-square/DUTY1-0.2/modElectronsIemission-10.0/phiSweep/']
    # for i,subDir in enumerate(subDirs):
    #     print('###################################\n')
    #     print("Processing '%s'..."%subDir)
    #     print('###################################\n')
    #     SDD = SweepDataDir(subDir)
    #     SDD.plotRelevantHistories(ow=ow,freq='all',nc=nc)
    #     # SDD.plotDr(partTypes='electronsT',tagRatio=0.1,xy=['x','y'],uxy=['ux','uy'],bins=50,nc=nc)
        
        
    #     # SDD.plotRelevantParticles(partTypes=partTypes,steps=steps,bins=bins,cutoffWeight=cutoffWeight,freq=True,ow=ow,nc=nc)
    #     # SDD.plotRelevantParticles(partTypes=partTypes,steps=steps,bins=bins,cutoffWeight=cutoffWeight,freq=False,ow=False,nc=nc)
        
    #     SDD.plotCycloidData(partTypes=['electronsT','modElectronsT'],bins=bins[:2],freq=True,nc=nc)
    #     SDD.plotCycloidData(partTypes=['electronsT','modElectronsT'],bins=bins[:2],freq=False,nc=nc)
        
    #     # SDD.plotRelevantFields(fieldTypes=fieldTypes,freq=True,polar=False,nc=nc)
    #     # SDD.plotRelevantFields(fieldTypes=fieldTypes,freq=False,polar=False,nc=nc)

    #     # SDD.saveParticlesImgs( partTypes=['electronsT'],saveLoc=None,freq=False,frameSkip=frameSkip,write=True,ow=ow,nc=nc)
    #     # SDD.saveParticlesImgs( partTypes=['electronsT'],saveLoc=None,freq=True,frameSkip=frameSkip, write=True,ow=False,nc=nc)
    #     # SDD.saveMp4s()
    #     progress = (i+1)/len(subDirs)*100
    #     print('\n###################################\n')
    #     print("Processing '%s'... Done\n"%subDir)
    #     print('Sweep Processing Total Progress: %0.2f%%'%(progress))
    #     print('\n###################################\n')
    ######################
    #    ???
    ###################### 
    
    # mi = DF.index
    # theVars = SDD.getVarsFromMI(mi,dtype='DataFrame')
    # baseName = SDD.genBaseName(theVars.iloc[0].to_dict())
    # SDD.plot2DSweeps(DF,histNamesP='Pout')
    # fig,ax = SDD.DFM.plot1Ds(DF['spokePhase'],fig=1)
    # fig.canvas.draw()
    
    
    ######################
    #    plot pre var
    ###################### 
    # folder = '/media***REMOVED******REMOVED***/Documents/SCLC_data/2023/WSweep/V-1e3/BETA-1.0/' 
    # SDD = SweepDataDir(folder,quickOpen=False)
    # DF = SDD.getRelVars(['DX','W_ANODE'])
    # DF = DF.set_index('W_ANODE')
    # fig,ax = SDD.DFM.plot1D(DF,axType = 'semilogx',marker='o')
    
    
    ######################
    #    process sweep dir
    ###################### 
    
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/2023/vbSweep/NXY-109/' 
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/2023/vbSweep/NXY-109/feaEmitter-1/iCathode-1000/vbRatio-665e3/PRF_AVG-450e3/BSTATIC-0.16/'
    # # sweepVars = ['PARTICLES','I_CATHODE','PRF_AVG','FREQ','BSTATIC','VDC']
    # saveName = 'sweepData'
    # relVars = ['electronsIemit','electronsIanode','electronsIcathode','PRF_AVG','FREQ','BSTATIC','VDC',
    #             'rEndHatEmit0','modElectronsSwitch','modElectronsIemit','modElectronsIanode',
    #             'PHISTART','DUTY1']
    
    # nc = 1
    # ow = True
    
    # SDD = SweepDataDir(folder,quickOpen=(not ow))
    # DF = SDD.processSweep(histNamesP='Pout',histNamesV='Vout',histNamesRho='RhoCircleR05',histNamesE='EedgeCircleR05',relVars=relVars,nc=nc,ow=ow)
    # np.seterr(divide='ignore')
    # DF['Pout*'] = DF['Pout'] - DF['modElectronsIanode']*DF['VDC']
    # DF['gain'] = 10*np.log10(np.divide(DF['Pout'],DF['PRF_AVG']))
    # # # SDD.plot2DSweeps(DF,histNamesP='Pout')
    # # pd.set_option('expand_frame_repr', True)  # print DataFrames in the terminal without omission
    # # print(DF)
    
    
    # DF = DF.rename({'PRF_AVG':'Pin'},axis=1)
    # DF.to_hdf(folder + saveName + '.h5' ,key='df',format='fixed')
    # DF.to_excel(folder+saveName + '.xlsx')
    
    # # # In[0] plotting

    # # ######## plotting setup
    # xVar = 'Pin'
    # yVar = 'Pout*'
    # DF = DF.dropna(axis=0,subset=['stable']).reset_index(drop=True)
    # # remove unstable PHISTARTS from the fea emitters
    # DFplot = copy.deepcopy(DF.loc[ (DF['modElectronsSwitch']==0) ] )
    # DFtemp = DF.loc[(DF['modElectronsSwitch']==1) & (DF['stable']==1) ].groupby(['modElectronsIemit','rEndHatEmit0','PRF_AVG']).max().reset_index()
    # DFplot = pd.concat([DFplot,DFtemp])
    # DFplot[xVar] = DFplot[xVar]/1e3  # [kW]
    # DFplot[yVar] = DFplot[yVar]/1e6        # [MW]
    # DFplot['VDC'] = DFplot['VDC']/1e3          # [kV]
    
    # # # ######## plotting using hvplot
    # import hvplot.pandas
    # import hvplot as hv
    # import hvwrap 
    # DFplot['marker'] = 'x'
    # DFplot['marker'].loc[DFplot['modElectronsSwitch']==0] = 'triangle'
    # # DFplot['marker'].loc[DFplot['electronsIemit'].abs()<150] = 'triangle'
    # DFplot['color'] = DFplot['stable'].map({1:'b',0:'r'})
    # #DFplot['legend'] = DFplot['marker'].map({'x':'eh=on','circle':'eh=off','triangle':'sclc=False'})
    
    # # options
    # # ('PRF_AVG', "@PRF_AVG kW")
    
    # hover = bk.models.HoverTool(tooltips=[(yVar, "@%s MW"%yVar),
    #                                       ("gain", "@gain dB"),
    #                                       ("VDC", "@VDC kV"),
    #                                       ("BSTATIC", "@BSTATIC T")])
    
    # hoverCols = ['gain','VDC','BSTATIC']
    # # hover_cols=['rEndHatEmit0','DUTY1','PHISTART']
    # # DFuniform = DF.loc[DF['electronsIemit']<150]
    # DFplot = DFplot.loc[DFplot[xVar]!=0]
    # width = 1000
    # height = 500
    # dpi = 108
    # fig = DFplot.hvplot.scatter(x=xVar, y=yVar,marker='marker',by='stable',
    #                         hover_cols=hoverCols,
    #                         width=width,height=height,logx=True,logy=True,
    #                         tools=[hover],
    #                         fontsize={'title': '50pt', 'ylabel': '20px', 'xlabel': '20px','ticks': 20,'legend':'20pt'},
    #                         size=200,
    #                         ylabel='Pout [MW]',
    #                         xlabel='Pin [kW]',
    #                         xlim=[40,500],
    #                         ylim=[1,15])
    
    # hvfig = hvwrap.hvshow(fig, 'bokeh', return_mpl=True)
    # saveLoc = folder
    # saveName = 'Pout-Pin'
    # hv.save(fig,saveLoc+saveName+ '.' + SDD.P.saveType,fmt=SDD.P.saveType)
    # # hvfig = hvwrap.hvshow(fig, 'matplotlib')
    # # hvfig.set_size_inches(width/dpi, height/dpi)
    # #fig.savefig(saveLoc + saveName + '.' + SDD.P.saveType, bbox_inches='tight', format=SDD.P.saveType)
    # # ###### plot Pout vs Pdrive
    # # DF['PRF_AVG'] = DF['PRF_AVG']/1e3
    
    # # DF1 = DF.set_index(['PRF_AVG','Pout'])['stable']
    # # # SDD.DFM.scatterColor(DF1,fig=1)
    # # from hvwrap import hvshow
    # # hvfig = DF.hvplot.scatter(x='PRF_AVG', y='Pout', by='stable')
    # # hvfig = hvshow(hvfig, 'matplotlib')
    # # In[0] plotting ????
    # # df = pd.DataFrame(np.random.rand(10,2),columns=['A','B'])
    # # df['group'] = np.random.choice(4,size=10)
    # # df['category'] = np.random.choice(['CC','DD'],size=10)
    # # df['sizes'] = np.random.randint(10,50,size=10)
    # # # df['marker'] = df.category.replace("DD","x").replace("CC","c")
    # # df['marker'] = 'circle'
    # # df['marker'].iloc[0]='x'
    # # fig = df.hvplot.scatter(x='A',y='B', color="group", size="sizes", marker="marker",logx=True,logy=True)
    # # hvfig = hvwrap.hvshow(fig, 'bokeh', return_mpl=True)
    
    
    # ############## plotting using matplotlib
    # figsize=(12,7)
    # fig,ax = SDD.DFM.checkFig(fig=1,figsize=figsize,clear=True)
    
    # xlim = [40,500]
    # ylim=[1,15]
    # gainLines = np.array([10,15,20])
    # # add constant gain lines
    # x = np.array(xlim)
    # for gainLine in gainLines:
    #     y = 10**(gainLine/10)*x*1e3/1e6
    #     ax.plot(x,y,linestyle='--',color='k')
    
    # DFtemp = DFplot.loc[ (DFplot['modElectronsSwitch']==0) & (DFplot['stable']==0) ].set_index('PRF_AVG')['Pout']
    # fig,ax = SDD.DFM.scatter(DFtemp,fig=fig,figsize=figsize,clear=False,marker='x',color='b',label='EHE Off, unstable')
    
    # DFtemp = DFplot.loc[ (DFplot['modElectronsSwitch']==0) & (DFplot['stable']==1) ].set_index('PRF_AVG')['Pout']
    # fig,ax = SDD.DFM.scatter(DFtemp,fig=fig,figsize=figsize,clear=False,marker='o',color='b',label='EHE Off, stable')
    
    # DFtemp = DFplot.loc[ (DFplot['modElectronsSwitch']==1) & (DFplot['stable']==1) ].set_index('PRF_AVG')['Pout']
    # fig,ax = SDD.DFM.scatter(DFtemp,fig=fig,figsize=figsize,clear=False,marker='o',color='r',label='EHE On, stable')
    
    
    
    
    # ax.set_xscale("log")
    # ax.set_yscale("log")
    
    # ax.set(xlim=xlim)
    # ax.set(ylim=ylim)
    # # ax.grid(True)
    # # add constant gain lines
    
    # from matplotlib.ticker import ScalarFormatter
    # for axis in [ax.xaxis, ax.yaxis]:
    #     axis.set_major_formatter(ScalarFormatter())
    #     axis.set_minor_formatter(ScalarFormatter())
        
    # ax.grid(True)
    
    
    ######################
    #    cycloid radius
    ###################### 
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/VBsweep/PRF_AVG-450e3/BSTATIC-0.140/'
    # nc = 16
    # SDD = SweepDataDir(folder)
    # SDD.plotDrData(partTypes='electronsT',tagRatio=.1,saveLoc=None,nc=nc)
    
    ######################
    #    ?????????
    ###################### 
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/VBsweep/PRF_AVG-450e3/BSTATIC-0.140/'
    # nc = 16
    # SDD = SweepDataDir(folder)
    # # DF = SDD.DFM.getStableWidth(DF,iSweep='VDC',checkCols=['VDC'],stableCol='stable')
    # DF = SDD.DFM.getStableData(DF,method='width',iSweep='VDC',checkCols=['VDC'],stableCol='stable')
    # DF = SDD.DFM.getStableData(DF,method='max',iSweep='VDC',checkCols=['Pout'],stableCol='stable')
    # pd.set_option('expand_frame_repr', False)  # print DataFrames in the terminal without omission
    # print(DF)
    # DF = SDD.genLookupDF()

    
    ######################
    #    ploting methods
    ###################### 
    
    folder = '/home/***REMOVED***/Documents/CFAdata/2025/VBSweep/NXY-109/TEND-300e-9/'
    folder = '/media***REMOVED***FASTER/magnetronData/2024/DXY_FACTOR-2/GRID_ALIGN-1/cathodeAlignment-odd/MANUAL_DECOMP-2/PRIME_SIGNAL-0/Iemit-1000/'
    sweepVars = {'BSTATIC':3,'PRF_AVG':0,'VDC':1}
    
    # folder = '/home/***REMOVED***/Documents/CFAdata/2025/anodeOffsetSweep/'
    # folder = '/media***REMOVED***FAST/CFAdata/2023/anodeOffsetSweep/NXY-109/tend-300e-9/'
    # sweepVars = {'FREQ':3,'PRF_AVG':0,'VDC':1,'angleOffset':2}
    
    # folder = '/home/***REMOVED***/Documents/CFAdata/2025/magOffsetSweep//'
    # sweepVars = {'DMFRAC':2,'FREQ':3,'iCathode':0,'PRF_AVG':0,'VDC':1,'angleOffset':2,'magOffset':1}
    
    
    # folder = ''
    
    # # folder = '/home***REMOVED***Documents/fastData/coaxData/2024/vSweep/Iemit-1000/BSTATIC-0.150/'
    # # folder = '/home***REMOVED***Documents/fastData/coaxData/2024/vSweep/Iemit-20/BSTATIC-0.150/'
    nc=32
    cutoffWeight = 0.01
    SDD = SweepDataDir(folder)
    # SDD.sweepDirs = SDD.sweepDirs[:6]
    partTypes=['electronsT','modElectronsT',['electronsT','modElectronsT']]
    bins = [100,150]
    # partTypes=['electrons','electronsT']
    fieldTypes=['E']
    steps = 'all'
    # steps = range(1000,1300)
    ow=False
    plotLockIn = True
    
    # 
    # delayHours = 1.5
    # delaySecs = delayHours*60*60
    # print('Delay set: waiting %0.1f hours before processing...'%delayHours)
    # sleep(delaySecs)
    
    
    # histNames = ['secElectronsIabsTheAnodeAbsorber','electronsIabsTheAnodeAbsorber']
    # DF1 = SDD.getScalerSweepData(histNames)
    # DF1 = DF1.sum(axis=1).to_frame('Ianode')
    # histNames = ['electronsIemitTheCathodeEmitter']
    # DF2 = SDD.getScalerSweepData(histNames)
    # DF2.columns = ['Iprime']
    # histNames = ['secElectronsIemitSecondaryEmitterFromPrimary','secElectronsIemitSecondaryEmitterFromSecondary']
    # DF3 = SDD.getScalerSweepData(histNames)
    # DF3 = DF3.sum(axis=1).to_frame('Isec')
    
    
    # fig,ax = SDD.DFM.plot1D(DF1.abs(),fig=1)
    # fig,ax = SDD.DFM.plot1D(DF2.abs(),fig=fig,clear=False)
    # fig,ax = SDD.DFM.plot1D(DF3.abs(),fig=fig,clear=False)
    #SDD.plotHistory(histName)

    # SDD.plotRelevantHistories(freq=True,ow=ow,sweepVars=sweepVars,nc=nc)
    # SDD.plotRelevantHistories(freq=False,ow=ow,sweepVars=sweepVars,nc=nc)
    # SDD.plotRelevantHistories(freq=None,ow=ow,sweepVars=sweepVars,nc=nc)
    
    # SDD.plotRelevantParticles(partTypes=partTypes,steps=steps,bins=bins,cutoffWeight=cutoffWeight,freq=True,ow=ow,plotLockIn=plotLockIn,sweepVars=sweepVars,nc=nc)
    # SDD.plotRelevantParticles(partTypes=partTypes,steps=steps,bins=bins,cutoffWeight=cutoffWeight,freq=False,ow=False,plotLockIn=plotLockIn,sweepVars=sweepVars,nc=nc)
    # SDD.plotFreqSpokes(nc=nc,sweepVars=sweepVars)
    
    # SDD.plotCycloidData(partTypes=['electronsT','modElectronsT'],bins=bins[:2],freq=True,nc=nc)
    # SDD.plotCycloidData(partTypes=['electronsT','modElectronsT'],bins=bins[:2],freq=False,nc=nc)
    # # SDD.plotRelevantFields(fieldTypes=fieldTypes,freq=True,polar=False,nc=nc)
    # # SDD.plotRelevantFields(fieldTypes=fieldTypes,freq=False,polar=False,nc=nc)
    
    # histNames = ['Pout']
    # SDD.plotScalerSweep(histNames)
    
    # # # SDD.plotSpectrograms()
    # SDD.saveParticlesImgs(partTypes=[partTypes[-1]],saveLoc=None,freq=False,ow=ow,nc=nc)
    # SDD.saveParticlesImgs(partTypes=[partTypes[-1]],saveLoc=None,freq=True,frameSkip=1,ow=False,nc=nc)
    
    # # # SDD.saveParticlesImgs(partTypes='electronsT',saveLoc=None,freq=True,cCol='uphi',nc=nc)
    # # # SDD.saveParticlesImgs(partTypes='electronsT',saveLoc=None,freq=False,cCol='uphi',nc=nc)
    
    
    
    # SDD.saveMp4s(overwrite=True)
    
    # # SDD.plotDr(partTypes=partTypes,tagRatio=0.1,xy=['x','y'],uxy=['ux','uy'],bins=50,nc=nc)
    
    
    ##### summary stuff
    # SDD.cleanDirectories(relevantH5 = ['_phi.t_freq-0','_phi.t_freq-1','_r.phi_freq-0','_r.phi_freq-1',],nc=nc)
    # SDD.generateParticleFiles(partType='electronsT',relevantH5='_phi.t_',freq=True,nc=nc)
    
    varList = ['magOffset','angleOffset']
    # varList = []
    # SDD.generateSummaries(varList=varList,ow=True,nc=nc)
    # DF = SDD.combineSummaries(saveLoc=None,saveName=None,nc=nc)
    # 
    # exists = SDD.checkForParticleFiles(partType='electronsT',relevantH5='_phi.t_',nc=nc)
    
    
    # SDD.cleanDirectories(relevantH5 = '_phi.t_',nc=8)
    
    # ######################
    # #    generate lookup file
    # ###################### 
    # folder = '/home***REMOVED***Documents/fastData/CFAdata/2023/vSweep/'
    # # folder = '/home/***REMOVED***/Documents/CFA_data/2023/VBSweeps/'
    # SDD = SweepDataDir(folder)
    
    # DF = SDD.genLookupDF(varList=['N_PORT_LENGTH','NXY'])
    # executionTime = (time.time() - startTime)/60./60.
    # print('########  Finished Post-Processing   ##########')
    # print('Execution time: %.2f hours' %(executionTime))
    # pass
    
    
    # ######################
    # #    plot generic histories
    # ###################### 
    folder = '/media***REMOVED***FASTER/magnetronData/2024/DXY_FACTOR-2/GRID_ALIGN-1/cathodeAlignment-odd/MANUAL_DECOMP-2/PRIME_SIGNAL-0/Iemit-1000/'
    histNames = ['Poynting_AntennaPort']
    histNames = ['electronsIabsTheAnodeAbsorber', 'electronsIabsTheCathodeAbsorber','electronsIemitTheCathodeEmitter']
    histNames = ['Vdc0']
    nc=1
    SDD = SweepDataDir(folder)
    
    DF = SDD.getHistory(histNames,varDepth=3,nc=nc)
    #DF = DF.rolling(1000).mean()
    SDD.plotHistoryDF(DF,plotType='multiple',nc=nc,xlim=(0,20))
        
    
    