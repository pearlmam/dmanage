#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 18 18:37:03 2021

@author: marcus
"""

import shutil
import os
import getpass
import sys
# import paramiko
import select
import Xlib.support.connect as xlib_connect
import time
import subprocess as sp
from threading import Timer
import fcntl
import glob


import warnings
from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning)
    import paramiko


def nonBlockRead(output):
    fd = output.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return output.read()
    except:
        return ''

class Server():
    """class for sending files and running scripts to a server
    
    In order to connect, you must setup ssh keys with the server, currently
    no password option exists for security. 
    to setup ssh keys
    
    1. on local machine: ssh-keygen -t rsa
	$ note if one is already created, then cancel it upon overwrite prompt
	2. from local /$home/.ssh/id_rsa.pub append key on remote machine authorized_keys file in .ssh/authorized_keys
	$ cat ~/.ssh/id_rsa.pub | ssh mpearlman@r1.***REMOVED***.edu 'cat >> .ssh/authorized_keys'
	create the folder and file if needed
	3. ESURE PROPOR PERMISSIONS: ~/.ssh/authorized_keys file needs 700 permission
	$ chmod 700 ~/.ssh/authorized_keys
    
    """
    def __init__(self, computer='local',user=None):
        """instantiates a Server class for a specific server
        

        Parameters
        ----------
        computer : string, optional
            name or ip address of the computer. The default is 'local'.
        user : string, optional
            username to connect with. The default is None.

        Returns
        -------
        None.

        """
        
        
        if user is None:
            user = getpass.getuser()
        self.computer = computer
        self.user = user
        # self.thisScript = os.path.realpath(__file__)
        # self.thisScriptLoc = os.path.dirname(self.thisScript) + '/'
        # self.workspace = 'dmanageWorkspace/'
        # if not computer == 'local':
        #     self.connect()
    
    def connect(self):
        """ Connect to the server
        
        opens ssh and sftp connections to the server
        """
        if not self.computer == 'local':
            print('connecting...')
            self.comp = paramiko.SSHClient()	# setup the client variable
            # allow modification of host_key.  This is the local list of allowed connections
            self.comp.set_missing_host_key_policy(paramiko.AutoAddPolicy())	
            self.comp.connect(self.computer, username=self.user)
            self.sftp = self.comp.open_sftp()  # open a ftp connection
            print('connected!')
            return self.comp
    
    def connectX(self):
        """NOT WORKING. use subprocess to ssh -X and run the command
        
        Used to pass X through ssh in paramiko sp I can plot
        
        """
        local_x11_display = xlib_connect.get_display(os.environ['DISPLAY'])
        local_x11_socket = xlib_connect.get_socket(*local_x11_display[:4])
        transport = self.comp.get_transport()
        session = transport.open_session()
        session.request_x11(single_connection=True)
        session.exec_command('xterm')
        x11_chan = transport.accept()
        
        session_fileno = session.fileno()
        x11_chan_fileno = x11_chan.fileno()
        local_x11_socket_fileno = local_x11_socket.fileno()
        
        poller = select.poll()
        poller.register(session_fileno, select.POLLIN)
        poller.register(x11_chan_fileno, select.POLLIN)
        poller.register(local_x11_socket, select.POLLIN)
        while not session.exit_status_ready():
            poll = poller.poll()
            if not poll: # this should not happen, as we don't have a timeout.
                break
            for fd, event in poll:
                if fd == session_fileno:
                    while session.recv_ready():
                        sys.stdout.write(session.recv(4096))
                    while session.recv_stderr_ready():
                        sys.stderr.write(session.recv_stderr(4096))
                if fd == x11_chan_fileno:
                    local_x11_socket.sendall(x11_chan.recv(4096))
                if fd == local_x11_socket_fileno:
                    x11_chan.send(local_x11_socket.recv(4096))
        print('exit')
        while session.recv_ready():
            sys.stdout.write(session.recv(4096))
        while session.recv_stderr_ready():
            sys.stdout.write(session.recv_stderr(4096))
        session.close()
    
    def close(self):
        """ close the paramiko sessions
        
        """
        if not self.computer == 'local':
            self.sftp.close()
            self.comp.close()
    
#    def runScript(self, script, args=' '):
#        runLoc = os.path.dirname(script)
#        runLoc = os.path.join(runLoc,'')
#        
#        scriptName = os.path.basename(script)
#        self.command = 'cd ' + runLoc + ';pwd; python3 ' + scriptName + ' ' + args
#        
#        print(self.command)
#        stdin, stdout, stderr = self.comp.exec_command(self.command, procList = myJob.submitJobsMonitor(jobLocs, numProcs, numThreads)get_pty=True )
#        for line in stdout.readlines():
#            print(line)
#        for line in stderr.readlines():
#            print(line)   
    
    def runScript(self, script,conda=None, args=''):
        """ run the script using paramiko paramiko.SSHClient()
        
        this uses paramiko's ssh protocol to run the script

        Parameters
        ----------
        script : string
            path to the file.
        conda : string, optional
            conda environment to activate before calling the script. The default is None.
        args : string, optional
            args for the python script. the format is the sam as if you call 
            'python myScript.py arg0 arg1 ...'The default is ''.

        Returns
        -------
        None.

        """
        
        
        print('running script: %s'%(script))
        runLoc = os.path.dirname(script)
        scriptName = os.path.basename(script)
        self.command = ''
        if not conda is None:
            # note that .bashrc needs to initialize conda.
            # some .bashrc files dont run  "If not running interactively, don't do anything"
            # apparently, paramiko is not running interactivly... move the conda initialize above this line
            self.command = self.command + 'conda activate %s;'%(conda)
        self.command = self.command + 'cd ' + runLoc + '; nohup python3 ' + scriptName + ' ' + args
        if not self.computer == 'local':
            stdin, stdout, stderr = self.comp.exec_command(self.command, get_pty=True )
            print('\n       _________  SCRIPT OUTPUT  ____________\n')
            for line in stdout.readlines():
                print(line)
            for line in stderr.readlines():
                print(line)  
        else:
            subProc=sp.Popen(self.command, shell=True, executable='/bin/bash', stdout=sp.PIPE)
        # this waits for the command to finish. If you close the paramiko session, the remote command will terminate
        # As long as you dont close the paramiko session, the remote command will continue. 
        print(self.command)
            
    
    def runScriptX(self, script, args=''):
        """Run script through ssh terminal and pass X for graphics
        
        This uses the subprocess module to ssh into the server and execute a script
        I dont remember if this works very well

        Parameters
        ----------
        script : string
            path to the file.
        args : string, optional
            args for the python script. the format is the sam as if you call 
            'python myScript.py arg0 arg1 ...'The default is ''.

        Returns
        -------
        None.

        """
        
        
        print('running script: %s'%(script))
        workspace = os.path.join(os.path.dirname(script),'')
        scriptname = os.path.basename(script)
        command = "ssh -X ***REMOVED***@***REMOVED*** 'cd " + workspace + ";nohup python3 " + scriptname + args + "'"
        #command = command.split(' ')
        #print(command)
        subProc=sp.Popen(command, shell=True, executable='/bin/bash', stdout=sp.PIPE, stderr=sp.PIPE)
        #self.checkSubProcRealTime(subProc, 1)
        
        print('\n       _________  SCRIPT OUTPUT  ____________\n')
        # both read stdout implemntations work but you must run once without any readline, and then
        # run with in order for it to work correclty
        
        # this implementation is a blocking readline, it hangs when there is no output, maybe.
#        if subProc.poll() is None:
#            for line in subProc.stdout.readlines():
#                print(line.decode('ascii').rstrip('\n'))
#
#        if subProc.poll() is None:
#            for line in subProc.stderr.readlines():
#                print(line.decode('ascii').rstrip('\n')) 
#        subProc.terminate()
#        
                
        # non-blocking readline. sometimes doesnt work... WTF
        loopCount = 0
        while (subProc.poll() is None):
            stdout = nonBlockRead(subProc.stdout)
            stderr = nonBlockRead(subProc.stderr)
            
            if stdout:
                print(stdout.decode('ascii').rstrip('\n'))
            if stderr:
                print(stderr.decode('ascii').rstrip('\n'))
            time.sleep(0.1)
            loopCount = loopCount+1
        subProc.terminate() 
        
        
    def putDir(self,source='./',target='~/', fileTypes=['all'],output=False):
        """Uploads the contents of the source directory to the target path. 
        
        All subdirectories in source are created under target. 
        TO DO: search through the directories and gather the file structure for
        to implement a progress bar.

        Parameters
        ----------
        source : string, optional
            local source of the directory to copy. The default is './'.
        target : string, optional
            Destination on the server to put the directory. The default is '~/'.
        fileTypes : list of strings, optional
            list of the file types to copy. Generally use extensions, like '.py', 
            but it can be any string pattern. If the string pattern is in the filename,
            the file will be transfered. The default is ['all'].
        output : bool, optional
            controls whether to print terminal output. The transfer progress is 
            not currently availiable. The default is False.

        Returns
        -------
        None.

        """
        hiddenPrefixes = ('_','.')
        if output: print("Transfering script files: \n    Source: '%s'\n    Target: '%s'"%(source,target))
        
        if not self.computer == 'local':
            self.mkdirR(target)
            if fileTypes[0]=='all':
                for item in os.listdir(source):
                    if os.path.isfile(os.path.join(source, item)):
                            self.sftp.put(os.path.join(source, item), '%s/%s' % (target, item))
                    elif item[0] not in hiddenPrefixes:
                        self.mkdirR('%s/%s' % (target, item))
                        self.putDir(os.path.join(source, item), '%s/%s' % (target, item))
            else:
                copyDirs = 'dir' in fileTypes
                for item in os.listdir(source):
                    if os.path.isfile(os.path.join(source, item)):
                        for fileType in fileTypes:
                            if fileType in item:
                                self.sftp.put(os.path.join(source, item), '%s/%s' % (target, item))
                    elif copyDirs and item[0] not in hiddenPrefixes:
                        self.mkdirR('%s/%s' % (target, item))
                        self.putDir(os.path.join(source, item), '%s/%s' % (target, item))
        else:
            if not os.path.exists(target):
                os.makedirs(target) 
            if fileTypes[0] == 'all':
                fileTypes[0] = '.*'
            
            files = []
            for fileType in fileTypes:
                files = files + glob.glob(os.path.join(source, '*' + fileType))
            for file in files:
                if os.path.isfile(file):
                    shutil.copy2(file, target)
            

        
    def mkdir(self, path, mode=511, ignore_existing=False):
        """ Augments mkdir by adding an option to not fail if the folder exists  
        """
        try:
            self.sftp.mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise
    def mkdirR(self, remote_directory):
        """Change to this directory, recursively making new folders if needed.
        Returns True if any folders were created.
        """
        if remote_directory == '/':
            # absolute path so change directory to root
            self.sftp.chdir('/')
            return
        if remote_directory == '':
            # top-level relative directory must exist
            return
        try:
            self.sftp.chdir(remote_directory) # sub-directory exists
            
                
        except IOError:
            dirname, basename = os.path.split(remote_directory.rstrip('/'))
            self.mkdirR(dirname) # make parent directories
            self.sftp.mkdir(basename) # sub-directory missing, so created it
            self.sftp.chdir(basename)
            return True
        # print('directory exists: %s'%remote_directory)
        # # ??? delete contents
        # filesToRemove = self.sftp.listdir(path=remote_directory)
        # print('removing files: %s'%filesToRemove)
        # for file in filesToRemove:
        #     print('removing: %s'%(remote_directory+file))
        #     self.sftp.remove(remote_directory+file)
        
       
    def checkSubProcRealTime(self,subProc, delay):
        """NOT WORKING
        
        Check the output of the subProcess in realtime. The output is 
        written to outFile periodically at time intervals defned by delay 

        Parameters
        ----------
        subProc : TYPE
            DESCRIPTION.
        delay : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
 
        check=None
        output = ''

        t = Timer(delay, dummy)
        t.start()
        while  check is None:
            data = subProc.stdout.readline()
            line = data.decode('ascii')
            print(line.rstrip())

            if not t.isAlive(): 
                t = Timer(delay, dummy)
                t.start()
                check =subProc.poll()
        return
    

def dummy(): 
	pass

if __name__ == "__main__":
    #######################################
    #      for job submission
    #######################################
    # --------------------------------------------
    # CFA Submit
    # --------------------------------------------
    # today = date.today()
    # theYear = today.strftime("%Y")
    # theDate = today.strftime("%m.%d.%y")
    # sourceDir = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/VSimModels/CFA/'
    # # sourceDir = '/home***REMOVED***Documents/fastData/CFAdata/2023/VBSweep/CFATemplate/'
    # # sourceDir = '/home/***REMOVED***/Documents/CFA_data/2023/VBSweeps/PARTICLES-1/I_CATHODE-60/PRF_AVG-150e3/FREQ-1.30/BSTATIC-0.140/'
    # scriptDir = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/pythonScripts/DataManagment/'
    
    # # workspace = '/home/***REMOVED***/Documents/CFA_data/%s/date-%s/VSweep/PARTICLES-1/thermalEnergy01Phi-200/thermalenergy01R-10/'% (theYear,theDate)
    # # workspace = '/home/***REMOVED***/Documents/SCLC_data/%s/date-%s/WSweep/BETA-0.1/'% (theYear,theDate)
    
    # setVarsDict = {'rEndHatEmit0':'0.1', 'profile':'sinePulse', 'DUTY1':'0.2', 'modElectronsIemission':'10.0', 'PRF_AVG':'150e3'}
    # varString = genSaveLoc(setVarsDict)
    
    # workspace = '/home/***REMOVED***/Documents/CFA_data/%s/date-%s/feaEmitter-1/%s/PHIsweep/' %(theYear,theDate,varString) 
    # # workspace = '/home/***REMOVED***/Documents/CFA_data/'
    # # workspace = '/home***REMOVED***Documents/fastData/CFAdata/'
    
    # script = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/pythonScripts/DataManagment/jobSubmit.py'
    # ECEsim = Server(computer='***REMOVED***.***REMOVED***.edu')
    # ECEsim.putDir(sourceDir,workspace,['.mac','.pre'])

    # # tempScriptName = 'jobSubmit_date-%s.py'%(date)
    # # ECEsim.put(script,workspace+tempScriptName)
    # # ECEsim.runScript(workspace+tempScriptName) 
    
    # scriptSpace = workspace + 'runScripts/'
    # ECEsim.putDir(scriptDir,scriptSpace,['all'],output=True)
    # ECEsim.runScript(scriptSpace + 'jobSubmit.py') 
    
    # ECEsim.close() 
    
    
    # --------------------------------------------
    # SCLC Submit
    # --------------------------------------------
    # today = date.today()
    # theYear = today.strftime("%Y")
    # theDate = today.strftime("%m.%d.%y")
    # sourceDir = '/home***REMOVED***Documents/SimulationProjects/sclc/VSimModels/parallelPlateES/'
    # scriptDir = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/pythonScripts/DataManagment/'
    
    # workspace = '/home/***REMOVED***/Documents/SCLC_data/%s/date-%s/USE_CL-True/WSweep/beta-0.0/'% (theYear,theDate)

    # script = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/pythonScripts/DataManagment/jobSubmit.py'
    # ECEsim = Server(computer='***REMOVED***.***REMOVED***.edu')
    # ECEsim.putDir(sourceDir,workspace,['.mac','.pre'])
    
    # scriptSpace = workspace + 'runScripts/'
    # ECEsim.putDir(scriptDir,scriptSpace,['all'],output=True)
    # ECEsim.runScript(scriptSpace + 'jobSubmit.py') 
    
    # ECEsim.close() 
    
    #######################################          
    # for data analysis
    #######################################
    # computer='***REMOVED***.***REMOVED***.edu'
    computer='***REMOVED***.***REMOVED***.edu'
    user='***REMOVED***'
    ECEsim = Server(computer=computer,user=user)
    ECEsim.connect()
    args = ''
    # # scriptName = 'CFAplot.py'
    # # scriptName = 'dataDir.py'
    # scriptName = 'sweepDir.py'
    # scriptName = 'analysers/summaryGainAnalysis.py'
    scriptName = 'analysers/dataSummaryPlots.py'
    # #scriptName = 'analysers/xcorrWindow.py'
    # #scriptName = 'analysers/dispersionSFFT.py'
    # #scriptName = 'analysers/dispersionXcorr.py'
    # #scriptName = 'analysers/electronAnalysis.py'
    # #scriptName = 'analysers/STFFT.py' 
    # scriptName = 'analysers/analyseFrequencyModulation.py' 
    # # scriptName = 'analysers/FFTSimExpSweepDir.py' 
    workspace = '/home/***REMOVED***/Documents/PythonProcessWorkspace/'
    

    # ##### Job Submit script params
    # simModel = 'hopFunnelEMcyl'
    # if simModel == 'hopFunnelEMcyl':
    #     sourcePreDir = '/home***REMOVED***Documents/SimulationProjects/hopFunnel/VSimModels/hopFunnelEMcyl'
    #     runBaseLoc = '~/Documents/hopFunnelData/'
    #     destPreDir = '/home/***REMOVED***/Documents/preWorkspace/hopFunnelEMcyl/'
    # elif simModel == 'CFA':
    #     sourcePreDir = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/VSimModels/CFA/'
    #     runBaseLoc = '~/Documents/CFAdata/'
    #     destPreDir = '/home/***REMOVED***/Documents/preWorkspace/CFA/'
        
    # scriptName = 'jobSubmit.py'
    # VSimDir = '~/Programs/VSim-12.3/'
    # loadVSimModule = False
    
    # maxProcs=32
    
    # ECEsim.putDir(sourcePreDir,destPreDir,['.mac','.pre'],output=True)
    # args = ' --preLoc %s --runBaseLoc %s --VSimDir %s --loadVSimModule %s --maxProcs %s'%(destPreDir, runBaseLoc,VSimDir,loadVSimModule,maxProcs)
    # workspace = '/home/***REMOVED***/Documents/PythonSubmitWorkspace/'
    ### args = args + '> nohup2.out'
    
    
    ######  run the script on remote Server
    
    workspace = workspace
    script = '/home***REMOVED***Documents/CFA_L-4953/pythonScripts/DataManagment/' + scriptName
    sourceDir = '/home***REMOVED***Documents/SimulationProjects/CFA_L-4953/pythonScripts/DataManagment/'
    # ECEsim.putDir(sourceDir,workspace,['.py'],output=True)
    ECEsim.putDir(sourceDir,workspace,['all'],output=True)
    
    ECEsim.runScript(workspace+scriptName,conda='data-manage',args=args) 
    ECEsim.close() 
    



