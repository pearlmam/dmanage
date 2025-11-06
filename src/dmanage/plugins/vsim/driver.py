# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 28 16:42:16 2021

@author: marcus
"""
import shutil
import os
import re
import sys
import argparse

import subprocess as sp
import select               # for non-block readline()
import multiprocessing as mp
import glob
from threading import Timer
from time import sleep
import numpy as np


import datetime
import time

from pathlib import Path
import natsort

from dmanage.utils.utils import isIterable
from dmanage.unit import makeDataUnit
from dmanage.plugins.vsim import loader
# possible fix for zombie creation. 
# see https://stackoverflow.com/questions/34007194/issue-with-pythons-subprocess-popen-creating-a-zombie-and-getting-stuck
# and https://docs.python.org/3/library/multiprocessing.html

#if __name__ == '__main__':
#    mp.set_start_method('spawn')
#    mp.freeze_support()


# dummy function used for Timer
def dummy(): 
	pass

class VSimInfo():
    def __init__(self, VSimDir):
        self.VSIM_DIR=VSimDir
        self.VSIM_BIN_DIR= self.VSIM_DIR + 'Contents/engine/bin/'
        self.VSIM_LIB_DIR=self.VSIM_DIR + 'Contents/engine/lib/'
        self.VSIM_SHARE_DIR=self.VSIM_DIR + 'Contents/engine/share/'
        self.df='datefudge "2021-05-01 00:00" '
    
class VSimJob():
    def __init__(self, VSimDir='~/Programs/VSim-12.3/',unloadModules=[],loadModules=[],maxProcs=32): 
        #self.jobName = jobName
        #self.jobLoc=jobLoc
        #self.preLoc=preLoc
        self.outFile = 'output.log'
        self.VSimInfo = VSimInfo(VSimDir)
        self.maxProcs = int(maxProcs)
        self.unloadModules = unloadModules
        self.loadModules = loadModules
        return
    
    def writeTimingFile(self,folder,fileName='output.log',outputFileName='timingAnalysis.csv'):
        fileHandle = folder + fileName
        timingFileHandle = folder + outputFileName
        timingString = 'timingAnalysis:,'
        file = open(fileHandle) 
        timingOutput = ''
        for line in file:
             if re.search(timingString, line):
                 timingOutput = timingOutput +  line.replace(timingString,'')
        file.close()
        
        if os.path.isfile(timingFileHandle):
            os.remove(timingFileHandle)
        file = open(timingFileHandle, "x")
        file.write(timingOutput)
        file.close()
        return
    
    def submitJob(self,jobLoc,numProcs,delayCheck=5,fudge=0,queue=None,timing=-1,resume=False):
        # source ~/Programs/VSim-11.0/VSimComposer.sh > /dev/null
        # mpiexec -np 2 ~/Programs/VSim-11.0/Contents/engine/bin/vorpal -i CFA.pre
        preFile = glob.glob(jobLoc + '*.pre')[0]
        fileName = os.path.basename(preFile)
        self.repVars(preFile, 'NUM_PROCS', numProcs,throwError=False)
        self.repVars(preFile, 'timingPeriodicity', timing)
        currentDir=os.getcwd()
        # create sequence of commands
        suppressOutput = True
        commands = []

        timingAnalysisCore = False
        for unloadModule in self.unloadModules:
            commands.append("module unload %s"%unloadModule)
            commands.append(" && ")
        
        for loadModule in self.loadModules:
            commands.append("module load %s"%loadModule)
            commands.append(" && ")
        
        commands.append("source %sVSimComposer.sh > /dev/null" % self.VSimInfo.VSIM_DIR)
        commands.append(" && ")
        preprocess = 1
        if preprocess:
            baseName = os.path.splitext(fileName)[0]
            commands.append("txpp.py -q %s.pre"%(baseName))  # -q makes simple in file
            # commands.append("txppp.py -n %s.pre %s"%(baseName,baseName))
            if suppressOutput:
                commands.append(' &> /dev/null')
            commands.append(" && ")
            runInFile = True
            if runInFile:
                fileName = fileName.replace('.pre','.in')
        if fudge:
            commands.append(self.df)
        
        if numProcs > 1:
            bindToCore = False
            if bindToCore:
                binding = '--bind-to core'
            else:
                binding = ''
            commands.append("mpiexec -np %s %s %svorpal -i %s" % \
		                   (numProcs, binding,self.VSimInfo.VSIM_BIN_DIR,fileName))
            if not timingAnalysisCore:
                commands.append(' -nc')
        else:
            commands.append("%svorpalser -i %s" % \
		                   (self.VSimInfo.VSIM_BIN_DIR,fileName))
        if resume:
            DataDir = makeDataUnit(loader.VSim)
            DD = DataDir(jobLoc)
            steps = list(DD.Parts.stepNums.values()) + list(DD.Fields.stepNums.values())
            commonSteps = list(set.intersection(*map(set, steps)))
            if len(commonSteps)<1:
                raise Exception('jobSubmit() with option resume cannot determine the dump to start from, user must choose dump number by setting resume to an integer which is not implemented yet')
            else:
                lastValidDump = max(commonSteps)
            commands.append(' -r %i'%lastValidDump)
        
        if suppressOutput:
            commands.append(' 2> /dev/null')

        commands.append(" && ")
        commands.append("exit")
        command = ''.join(commands)
        
        # print(command)
        # execute the commands
        os.chdir(jobLoc)    # need to run from the pre-file directory
        #print('RUNNING: %s'%(preFile))
        startTime = time.time()
        subProc=sp.Popen(command, shell=True, executable='/bin/bash', stdout=sp.PIPE)
        errorOccured = self.checkSubProcRealTime(subProc, self.outFile, delayCheck)   # process hangs here until vorpal is done.
        date = (datetime.datetime.now().strftime('%Y-%m-%d %T'))
        jobLocStriped = Path(*jobLoc.split('/')[-3:])
        elapsedTime = (time.time() - startTime)/60./60.
        if errorOccured:
            print("ERROR %s: '.../%s/' in %.2f hours"%(date,jobLocStriped,elapsedTime))
        else:
            # delete old history file
            removeList = glob.glob('*_History.h5.backup')
            removeList = removeList + glob.glob('*_all_*')
            removeList = removeList + glob.glob('*_completed.txt')
            for item in removeList:
                try: os.remove(item)
                except: pass
            if timing > -1:
                self.writeTimingFile(jobLoc,fileName='output.log')
                if timingAnalysisCore:
                    commsList = glob.glob('*_comms_*')
                    commsList = natsort.natsorted(commsList)
                    for i,commFileName in enumerate(commsList):
                        self.writeTimingFile(jobLoc,fileName=os.path.basename(commFileName),outputFileName='timingAnalysis_%i.csv'%i)
            print("FINISHED %s: '.../%s/' in %.2f hours"%(date,jobLocStriped,elapsedTime))
        os.chdir(currentDir)
        if not queue is None:
            ret = queue.get()
            ret['error'] = errorOccured
            queue.put(ret)  
        return errorOccured
	
    def submitJobs(self,jobLocs,numProcs,nt,delayCheck=5,fudge=0,queue=None,timing=-1,resume=False):
        if type(numProcs) is not list:
            numProcs = [numProcs]*len(jobLocs)
        if len(jobLocs) > len(numProcs):
            print('Length of numProcs < Length of jobLocs')
            return
        procs = [None] * nt

        for i in range(nt):
            procs[i] = mp.Process(target=self.submitJob, args=(jobLocs[i], numProcs[i],delayCheck,fudge,queue,timing,resume))
            procs[i].start()
        return procs
    
    def checkActiveProcs(self):
        checkVorpalProc=sp.Popen('ps aux | grep Rsl | grep vorpa[l]', shell=True, executable='/bin/bash', stdout=sp.PIPE, stderr=sp.PIPE)
        output, err = checkVorpalProc.communicate()
        usedProcs = len(output.decode('ascii').split('\n'))-1
        return usedProcs
    
    def submitJobsMonitor(self, jobLocs,numProcs,nt,delayCheck=5,fudge=0,timing=-1,resume=False):
        """
        jobLocs: list of strings representing the paths
        numProcs: integer or a list of ints that represent the number of processors to use for each job in jobLocs
        nt: integer representing the number of threads to use
        
        This function submits the jobs, monitors the progress, then starts up new jobs as the processes free up
        
        """
        if jobLocs == None: return
        if type(numProcs) is not list:
            numProcs = [numProcs]*len(jobLocs)
        if len(jobLocs) > len(numProcs):
            print('Length of numProcs < Length of jobLocs')
            return
        numProcs = numProcs + [0]*nt
        finJobs = 0
        numJobs = len(jobLocs)
        #startTimes = np.repeate(time.time(),numJobs)
        queue = mp.Queue()
        errorOccured = {'error':False}
        queue.put(errorOccured)
        # queue = None
        procs = self.submitJobs(jobLocs=jobLocs,numProcs=numProcs,nt=nt,delayCheck=delayCheck,fudge=fudge,queue=queue,timing=timing,resume=resume)
        check = True
        # errorOccured = False
        while check:
            sleep(delayCheck*2)
            usedProcs = self.checkActiveProcs()
            freeProcs = self.maxProcs-usedProcs
            nextProcs = numProcs[finJobs+nt]
            #print('Used Procs = %d, Free Procs = %d, Next Procs = %d'%(usedProcs,freeProcs,nextProcs))
            # note: using "for proc in procs", writing to proc doesn't write to the procs pointer 
            for i in range(len(procs)):
                if not procs[i].is_alive() and freeProcs >= nextProcs:    # check if proc is finished
                    errorOccured = queue.get() # will block
                    # print('monitor error %s'%errorOccured)
                    if errorOccured['error']:
                        print('CATASTROPHIC ERROR OCURRED')
                        # check = False
                        # for proc in procs:
                        #     procs.terminate()
                    else:
                        procs[i].terminate() # prevent zombies??
                        finJobs = finJobs + 1
                        progress = finJobs/numJobs*100
                        queue.put(errorOccured)
                    print('Progress: %i/%i, %.1f%%'%(finJobs,numJobs,progress))
                    if finJobs <= numJobs-nt:                          # jobs availiable so start next job
                        j = finJobs+nt-1
                        procs[i] = mp.Process(target=self.submitJob,args=(jobLocs[j],numProcs[j],delayCheck,fudge,queue,timing,resume))
                        procs[i].start()
                        sleep(5) # wait for the job to be submitted so I can keep track of procs on the next loop
                        break  # need to break loop to check the number of procs and deal with it properly
                    elif (finJobs > numJobs-nt) and (finJobs <= numJobs-1): # no new jobs availiable, remove proc from list
                        procs.pop(i)
                        # needs to break the loop because the proclist is reduced in length. takes longer to realize each proc is done...
                        break
                    else:                                              # all jobs finished
                        check = False
                elif not procs[i].is_alive() and freeProcs <= nextProcs:
                    print('waiting for free procs...')
                else:
                    pass
        return procs
    
    def checkSubProcRealTime(self,subProc,outFile,delay):
        # Check the output of the subProcess in realtime. The output is 
        # written to outFile periodically at time intervals defned by delay 
        
        # initialize the while loop variables
        check=True
        checkOutput = True
        checkProc = True
        
        checkOutputCountMax = 1e12 # 60*10 # seconds  # High number means dont check
        checkOutputCountMax = checkOutputCountMax/delay
        output = ''
        checkOutputCount = 0
        errorOccured = False
        # This timer is used so that the while loop can read the lines.
        t = Timer(delay, dummy)
        t.start()
        # This object is for a non-blocking readline()
        poll_obj = select.poll()
        poll_obj.register(subProc.stdout, select.POLLIN)

        open(outFile, 'w').close()
        while check:
            # non-blocking readline
            poll_result = poll_obj.poll(0)
            if poll_result:
                data = subProc.stdout.readline()
                line = data.decode('ascii')
                #print(line.rstrip())
                # these warnings are in the nohup... how to ignore...
                # if 'SyntaxWarning' in line:
                #     pass   # do not add these warnings to output.
                # else:
                output=output+line
                # output=''
            else:
                time.sleep(delay/2)

            if not t.is_alive(): 
                if 'Input/output error' in output:
                    print('ERROR: detected Input/output error')
                    errorOccured = True
                    checkOutput = False
                elif output == '':
                    checkOutputCount += 1
                    # date = (datetime.datetime.now().strftime('%T'))
                    # print( "NO OUTPUT %s: job proc = %s"%(date,subProc.poll()) )
                    # print('no output: %i'%checkOutputCount)
                else:
                    # if 'OUTPUT SUMMARY:' in output:
                    #     # simulation has finished and is summarizing the sim, this can take a bit???
                    #     timeSummary = time.time()
                    #     checkOutputCountMax = 60*10/delay   # wait 10 minutes for the output???
                        
                    checkOutput = True
                    checkOutputCount = 0
                if checkOutputCount>checkOutputCountMax:
                    checkOutputTimeMax = checkOutputCountMax*delay
                    print('ERROR: No output for %.02f seconds'%checkOutputTimeMax)
                    errorOccured = True
                    checkOutput = False
                    
                # write output to file realtime
                with open(outFile, "a") as myfile:
                    myfile.write(output)
                    myfile.close()
                    
                output=''
                t = Timer(delay, dummy)
                t.start()
                
            checkProc = (subProc.poll() is None)
            check = (checkProc and checkOutput)

        
        # finish reading output
        if not errorOccured:
            data = subProc.stdout.read()
            lines = data.decode('ascii')
            #print(line.rstrip())
            output=output+lines
        
        # write final output to file
        with open(outFile, "a") as myfile:
            myfile.write(output)
            myfile.close()
        
        # executionTime = (time.time() - timeSummary)/60.
        # print('  output summary time %.2f minutes' %(executionTime))
        
        return errorOccured
    
    def spawnSweepDirs(self,preLoc,variables,values,jobLoc=None,protect=True):
        # make both list of lists
        if not isIterable(variables): variables = [variables]
        if not isIterable(values): values = [values]
        if not isIterable(values[0]): values = [values]
        if jobLoc==None: jobLoc=preLoc
        varLengths = len(variables)
        valueLengths = np.array([len(value) for value in values])    
        
        if not all(varLengths == valueLengths):
            raise Exception("the length of each value list must be equal to the number of variables!")
            
        jobSubLocs = []
        preFile = glob.glob(preLoc + '*.pre')[0]
        macFiles = glob.glob(preLoc + '*.mac')
        for value in values:
            jobSubLoc = jobLoc
            for variable,val in zip(variables,value):
                jobSubLoc = '%s%s-%s/'%(jobSubLoc,variable,val)
            jobSubLocs.append(jobSubLoc)
            
            if os.path.exists(jobSubLoc):
                #print('DELETED: %s'%(jobSubLoc))
                if protect:
                    print('folder exists, delete manually. Aborting')
                    sys.exit()
                #shutil.rmtree(jobSubLoc)
            else:
                os.makedirs(jobSubLoc)
            shutil.copy(preFile, jobSubLoc)
            histFileBackup = False
            if not histFileBackup:
                simName = os.path.basename(preFile)
                simName = os.path.splitext(simName)[0]
                histBackupFile = jobSubLoc + simName + '_History.h5.backup'
                os.symlink('/dev/null',histBackupFile)
            for macFile in macFiles: shutil.copy(macFile, jobSubLoc) 
            self.repVars(glob.glob(jobSubLoc + '*.pre')[0],variables,value,tag = '@@@',throwError=True)
        return jobSubLocs
    
    def repVarsSweepDirs(self, jobLocs,variables,values,throwError=True):
        for i,jobLoc in enumerate(jobLocs):
             self.repVars(glob.glob(jobLoc + '*.pre')[0],variables,values[i],tag = '@@@',throwError=throwError)
    
    def repVars(self,fileHandle,variables=None,values=None,varDict=None,tag = '@@@', preStr = '$ ',message='value replaced by sweep',throwError=False):
        """
        Open a file and change the parameter value. This function searches for the string specified by <tag>, default '@@@,' and replaces the parameters listed in <params> with the values specified in <values
        A backup file is also created with the same name <fileHandle> and '~' appended. 

        Parameters
        ----------
        fileHandle : str
            location of the file to edit.
        variables : str, list, optional
            parameters to edit. The default is None.
        values : str,list, optional
            Values to replace corresponding with the params. The default is None.
        varDict : TYPE, optional
            DESCRIPTION. The default is None.
        tag : str, optional
            tag in the file lines specifying that this value is to be replaced. The default is '@@@'.
        preStr : TYPE, optional
            DESCRIPTION. The default is '$ '.
        message : TYPE, optional
            DESCRIPTION. The default is 'value replaced by sweep'.
        throwError : TYPE, optional
            DESCRIPTION. The default is False.

        Raises
        ------
        ValueError
            DESCRIPTION.

        Returns
        -------
        None.

        """
        
        if (varDict is None) and ((variables is None) or (values is None)):
            raise ValueError('varDict must be defined or both params and values')
        elif (varDict is None):
            # check if params and values are a list
            if not isIterable(variables): variables = [variables]
            if not isIterable(values): values = [values]
            if len(variables) != len(values):
                raise ValueError('len(variables) != len(values), make the list lengths equal')
            varDict = dict(zip(variables, values))
        else: 
            pass  # it is a dict
        #print(params)    
        shutil.copy(fileHandle, fileHandle + '~')
        source = open(fileHandle + '~', 'r')
        dest = open(fileHandle, 'w')
        valueReplace = dict.fromkeys(varDict.keys(),False)
        for line in source:
            if (tag in line):
                writeString = line
                lineParam = line.split('=')[0].replace('$','').strip()
                #print(lineParam)
                for key,value in varDict.items():
                    #print(item.strip())
                    if key.strip() == lineParam:
                        writeString = preStr + key + ' = ' + str(value) + '  # @@@ %s\n'%message
                        #print(writeString)
                        valueReplace[key]=True
                dest.write(writeString)
            else: dest.write(line)
        dest.close()
        source.close()
        if (throwError) and (not all(valueReplace.values())):
            raise ValueError('All values not replaced: %s'%varDict)
        return


def rexists(sftp, path):
    """os.path.exists for paramiko's SCP object
    """
    try: sftp.stat(path)
    except IOError as e:
        if 'No such file' in str(e):
            return False
            raise
        else:
            return True
		
		
def mkdir_p(sftp, remote_directory):
    """Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created."""
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_directory == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory) # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdir_p(sftp, dirname) # make parent directories141818
        sftp.mkdir(basename) # sub-directory missing, so created it
        sftp.chdir(basename)
        return True

###### parser for command line inputs

def genArgParse(): 
    parser = argparse.ArgumentParser(description ='submit VSim Jobs')
    parser.add_argument('--preLoc', dest ='preLoc', action ='store', 
                        default=None, help ='location of the pre-file to run')
    parser.add_argument('--runBaseLoc', dest ='runBaseLoc', action ='store', 
                        default=None, help ='location of the run base directory to run. Will add set vars to the path')
    parser.add_argument('--VSimDir', dest ='VSimDir', action ='store', 
                        default=None, help ='location of the VSim directory')
    parser.add_argument('--fudge', dest ='fudge', action ='store', 
                        default=None, help ='whether to spoof the date')
    parser.add_argument('--unloadModules', dest ='unloadModules', action ='store', 
                        default=None, help ='list of modules to unload')
    parser.add_argument('--loadModules', dest ='loadModules', action ='store', 
                        default=None, help ='list of modules to load')
    parser.add_argument('--maxProcs', dest ='maxProcs', action ='store', 
                        default=None, help ='maximum number of threads allowed')

    return parser

def mapArgs(args,defaults):
    for key,value in args.items():
        if value is None:
            args[key] = defaults[key]
    return args


if __name__ == "__main__":
    pass    