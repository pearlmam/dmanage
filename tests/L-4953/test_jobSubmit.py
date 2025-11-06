# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import argparse
import os
import glob
import shutil
import datetime
import time
import itertools
 
from dmanage.utils.parser import genSaveString
from dmanage.plugins.vsim.driver import VSimJob,genArgParse,mapArgs

from dmanage.utils.mail import Mail

from test_sweepDir import MySweepDir

def printStore(output,totalOutput='',printOutput=True):
    if printOutput: print(output)
    totalOutput = totalOutput + output +'\n'
    return totalOutput


homeDir = os.getenv("HOME")
theYear = datetime.datetime.now().strftime("%Y")
theDate = datetime.datetime.now().strftime("%m.%d.%y")   



parser = genArgParse()
args = parser.parse_args()

###########################################
#       Inputs
###########################################
preLoc = '~/Documents/SimulationProjects/CFA_L-4953/VSimModels/CFA/'
runBaseLoc = '~/Documents/fastData/CFAdata/%s/date-%s/'%(theYear,theDate) 
setVarsDict = {'FREQ':'1.315e9','iCathode':'1000','BSTATIC':'0.140'}  

#----------------------------------------------
#      run engine Inputs
#----------------------------------------------
VSimDir = '~/Programs/VSim-12.3/'
fudge = False
maxProcs = 8
unloadModules = []
loadModules = []

coordProdGrid = False
testRun = True
resume = False

#----------------------------------------------
#      Sweep Inputs
#----------------------------------------------
numProcs = 2
numThreads = 4
delayCheck = 10    # delay to check the vorpal sims[seconds]
timing = -1

# ----------    var 1  --------------  
var1Name = 'PRF_AVG'
# var = np.logspace(-3,-1,6)
# var1s = [117,118,119,121,122,123]
var1s = [200,300,450]
var1Strs = [ '%0.0fe3' % i for i in var1s]


# ----------    var 2  --------------  
var2Name = 'VDC'
var2s = np.array([85,87,88,91,92,93,94,95,96,98])
var2s = var2s.tolist()
var2Strs = [ '%0.0fe3' % i for i in var2s]

#--------------     Package variables and values    --------------

variables = ['VDC']
var1s = [200,300,450]
var1s = [ '%0.0fe3' % i for i in var1s]
var2s = np.array([85,87,88,91,92,93,94,95])
var2s = var2s.tolist()
var2s = [ '%0.0fe3' % i for i in var2s]
values = [var2s]
values = list(itertools.product(*values))


#----------------------------------------------
#      Post process Inputs
#----------------------------------------------
postProcess = False
postProcessParticles = False
postProcessLockIn = True
postProcessHistories = '1D'   # '1D': only plot 1D hists, else plot all relevant hists
postProcessCycloidData = False    # cirulation period takes too long and parallel implementation blows up memory
postProcessFields = False
saveParticleImages = False
freq = False
tagRatio = 0.3
sweepVars = {'FREQ':3,'iCathode':0,'BSTATIC':3,'PRF_AVG':0,'VDC':1}  # for post process


#----------------------------------------------
#      mail Inputs
#----------------------------------------------
sendMail = True
senderMail = 'marcus.pearlman2@gmail.com'
password = 'bonglyoaxoxlqjti'
sendtoMail = 'marcus.pearlman@gmail.com'


###########################################
#       Start Jobs
###########################################

varString = genSaveString(setVarsDict)
runLoc = runBaseLoc + '%s/' %(varString)         
runLoc = runLoc.replace('~',homeDir)
preLoc = preLoc.replace('~',homeDir)

args = mapArgs(vars(args),locals())
if not os.path.exists(runLoc):
    os.makedirs(runLoc) 
files = glob.glob(os.path.join(preLoc, '*.pre')) + glob.glob(os.path.join(preLoc, '*.mac'))
for file in files:
    if os.path.isfile(file):
        shutil.copy2(file, runLoc)

# print(preLoc)
# print(runLoc)


myJob = VSimJob(VSimDir=args['VSimDir'],unloadModules=args['unloadModules'],loadModules=args['unloadModules'], 
                maxProcs=args['maxProcs']) # drhrbie: '~/Programs/VSim-11.0/'


startTime = time.time()
totalOutput = printStore('\n############   Running Sweep   ############\nSweep Directory: %s'%(runBaseLoc))



preFile = glob.glob(runLoc + '*.pre')[0]
myJob.repVars(preFile,varDict=setVarsDict,message='set variable by folder naming')
myJob.repVars(preFile,'NUM_PROCS',1)

jobLocs = myJob.spawnSweepDirs(runLoc,variables=variables,values=values,jobLoc=runLoc,protect=(not resume))

totalOutput = printStore('%s = %s'%(variables,values),totalOutput)
totalOutput = printStore('Number of Jobs: %d' % len(jobLocs),totalOutput)

# NOTE: submit the jobs at bottom of script for clean output


##########################################
#            for proper nohup output, leave uncommented    
##########################################
numThreads = min(numThreads,len(jobLocs))
numProcsStr = str(numProcs)
totalOutput = printStore('Computation Details: %d Thread(s), %s Core(s) each' % (numThreads, numProcsStr),totalOutput)
totalOutput = printStore((datetime.datetime.now().strftime('Started: %Y-%m-%d %T')),totalOutput)
totalOutput = printStore('###########################################\n',totalOutput)


##########################################
# submit sweep jobs   
##########################################
errorOccured = False
try:
    if not testRun:
        if coordProdGrid:
            coordProdThreads = min(numThreads*numProcs,len(jobLocs))
            totalOutput = printStore('########  Setting Up Coordinate Produced Grid  #######\n ',totalOutput)
            procList = myJob.submitJobsMonitor(jobLocs,1,coordProdThreads,delayCheck=0.5,fudge=fudge,timing=timing,resume=resume) # jobLocs=None: no jobs submitted
            totalOutput = printStore('############   Running Sweep   ############\n',totalOutput)
        procList = myJob.submitJobsMonitor(jobLocs,numProcs,numThreads,delayCheck=delayCheck,fudge=fudge,timing=timing,resume=resume) # jobLocs=None: no jobs submitted
    totalOutput = printStore('\n############   Finished Sweep   ############',totalOutput)
    
except:
    totalOutput = printStore('\n!!!!!!!!!!!!!!!   ERROR IN SWEEP   !!!!!!!!!!!!!',totalOutput)
    errorOccured = True
    

totalOutput = printStore(datetime.datetime.now().strftime('Finished: %Y-%m-%d %T'),totalOutput)
executionTime = (time.time() - startTime)/60./60.
totalOutput = printStore('Execution time: %.2f hours' %(executionTime),totalOutput)
totalOutput = printStore('###########################################\n',totalOutput)
if not postProcess:
    totalOutput = printStore('\n\nPost Processing is turned off!!!!!\n',totalOutput)
if sendMail:
    mail = Mail(senderMail,password)
    mail.sendDone(sendtoMail,content=totalOutput, outputFile=None)


###########################################
#  PostProcessing  
##########################################
if postProcess and not errorOccured and not testRun:
    totalOutput = printStore('\n#######################\n        Post Processing\n#######################\n',totalOutput)
    startTime = time.time()
    # determine the number of cores to use for post
    if type(numProcs) is list: nc = sum(numProcs[0:numThreads])
    else: nc = numProcs * numThreads
    saveLoc = runLoc + 'processed/'
    partTypes = ['modElectronsT','electronsT',['modElectronsT','electronsT']]
    fieldTypes=['E']
    bins = [100,150]
    posCols = ['r','phi']
    velCols = ['ur','uphi']
    try:
        totalOutput = printStore("Saving plots in '%s'"%saveLoc,totalOutput)
        SDD = MySweepDir(runLoc)
############################################################################################################   
        if postProcessHistories:
            
            if postProcessHistories == '1D':
                totalOutput = printStore("\n##########      plotRelevantHistories(freq=None), only 1D histories       ##########\n",totalOutput)
                SDD.plotRelevantHistories(sweepDirs=jobLocs,freq=None,sweepVars=sweepVars,nc=nc)
            else:
                totalOutput = printStore("\n##########      plotRelevantHistories(freq=False)      ##########\n",totalOutput)
                SDD.plotRelevantHistories(sweepDirs=jobLocs,freq=False,sweepVars=sweepVars,nc=nc)
                if freq:
                    totalOutput = printStore("\n##########      plotRelevantHistories(freq=True)      ##########\n",totalOutput)
                    SDD.plotRelevantHistories(sweepDirs=jobLocs,freq=True,sweepVars=sweepVars,nc=nc)
        else:
            totalOutput = printStore("\n##########      plotRelevantHisories Turned OFF      ##########\n",totalOutput) 
############################################################################################################   
        if postProcessParticles:
            totalOutput = printStore("\n##########      plotRelevantParticles(freq=False)      ##########\n",totalOutput)
            SDD.plotRelevantParticles(partTypes=partTypes,bins=bins,sweepDirs=jobLocs,freq=False,ow=False,plotLockIn=postProcessLockIn,sweepVars=sweepVars,nc=nc)
            if freq:
                totalOutput = printStore("\n##########      plotRelevantParticles(freq=True)",totalOutput)
                SDD.plotRelevantParticles(partTypes=partTypes,bins=bins,sweepDirs=jobLocs,freq=True,ow=False,plotLockIn=postProcessLockIn,sweepVars=sweepVars,nc=nc)
        else:
            totalOutput = printStore("\n##########      plotRelevantParticles Turned OFF      ##########\n",totalOutput)
############################################################################################################   
        if postProcessFields:
            totalOutput = printStore("\n##########      plotRelevantFields(freq=False)",totalOutput)
            SDD.plotRelevantFields(fieldTypes=fieldTypes,sweepDirs=jobLocs,freq=False,polar=False,nc=nc)
            if freq:
                totalOutput = printStore("\n##########      plotRelevantFields(freq=True)",totalOutput)
                SDD.plotRelevantFields(fieldTypes=fieldTypes,sweepDirs=jobLocs,freq=True,polar=False,nc=nc)
        else:
            totalOutput = printStore("\n##########      plotRelevantFields Turned OFF      ##########\n",totalOutput)
############################################################################################################   
        if postProcessCycloidData:
            totalOutput = printStore("\n##########      plotCycloidData(freq=False)",totalOutput)
            SDD.plotCycloidData(partTypes=['electronsT','modElectronsT'],bins=bins[:2],freq=True,nc=nc)
            if freq:
                totalOutput = printStore("\n##########      plotCycloidData(freq=True)",totalOutput)
                SDD.plotCycloidData(partTypes=['electronsT','modElectronsT'],bins=bins[:2],freq=False,nc=nc)
        else:
            totalOutput = printStore("\n##########      plotCycloidData() Turned OFF      ##########\n",totalOutput)
############################################################################################################   
        if saveParticleImages:
            totalOutput = printStore("\n##########      Saving particle images...      ##########\n",totalOutput)
            SDD.saveParticlesImgs(partTypes=[partTypes[-1]],sweepDirs=jobLocs,saveLoc=saveLoc,freq=False,nc=nc)
            if freq:
                SDD.saveParticlesImgs(partTypes=[partTypes[-1]],sweepDirs=jobLocs,saveLoc=saveLoc,freq=True,nc=nc)
        
            totalOutput = printStore("\n##########      Saving particle videos...      ##########\n",totalOutput)
            SDD.saveMp4s()
        else:
            totalOutput = printStore("\n##########      saveParticleImages() Turned OFF      ##########\n",totalOutput)
        
        if (postProcessParticles and freq) or postProcessHistories:
            varList = ['magOffset','angleOffset']
            SDD.generateSummaries(varList=varList,ow=True,nc=nc)
            DF = SDD.combineSummaries(saveLoc=None,saveName=None,nc=nc)
        
        
        # totalOutput = printStore("\n##########      Plotting cycloid radius...      ##########\n",totalOutput)
        totalOutput = printStore("\n##########      Plotting cycloid radius is turned off...      ##########\n",totalOutput)
        # SDD.plotDr(partTypes='electronsT',tagRatio=tagRatio,xy=['x','y'],uxy=['ux','uy'],bins=50,nc=nc)
        
        histNames = ['Pout']
        totalOutput = printStore("\n##########      Plotting scaler sweep for is turned off %s...      ##########\n"%(histNames),totalOutput)
        #totalOutput = printStore("\n##########      Plotting scaler sweep for %s...      ##########\n"%(histNames),totalOutput)
        #SDD.plotScalerSweep(diaList=histNames,methodDict={'self.DFM.reduce':{'iName':'t','method':'mean','theRange':[0.75,1.0]}},saveLoc=None,sweepDirs=None)
        
        totalOutput = printStore('########  Finished Post-Processing   ##########',totalOutput)
        totalOutput = printStore('Finished: %s' % datetime.datetime.now(),totalOutput)
        executionTime = (time.time() - startTime)/60./60.
        totalOutput = printStore('Execution time: %.2f hours' %(executionTime),totalOutput)
        totalOutput = printStore('###########################################\n',totalOutput)
    except Exception as e:
        executionTime = (time.time() - startTime)/60./60.
        totalOutput = printStore('Execution time: %.2f hours' %(executionTime),totalOutput)
        totalOutput = printStore('\n!!!!!!!!!!!!!!!   ERROR IN POST-PROCESSING   !!!!!!!!!!!!!',totalOutput)
        print(e)

    if sendMail:
        mail = Mail(senderMail,password)
        mail.sendDone(sendtoMail,content=totalOutput, outputFile=None)


cwd = os.path.join(os.getcwd(),'')
nohupCheck = glob.glob(cwd + '*.out')
if len(nohupCheck)>0:
    nohupFile = glob.glob(cwd + '*.out')[0]
    # nohupFile = cwd + 'nohup.out'
    nohupFilename = os.path.basename(nohupFile)
    if os.path.isfile(runLoc + nohupFilename):
        nohupFilename = nohupFilename.stem + '_2.out'
    if os.path.isfile(nohupFile):
        shutil.move(nohupFile, runLoc+nohupFilename) 







