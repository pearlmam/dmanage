#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  4 12:16:40 2022

@author: marcus
"""
from dmanage.ops.arrays.signal import get_phase, get_period
from dmanage.ops.arrays.vector import curl

import numpy as np
import glob
import subprocess as sp
import os
import shutil

def get_tags(fileName):
    pass


def save_mp4(directory, saveName=None, saveLoc=None, picType='png', overwrite=False):
        if saveLoc==None: saveLoc=directory
        
        # check if ffmpeg exists, and then try loading it
        if type(shutil.which('ffmpeg')) is type(None): 
            loadModule = True
            
            # cmd = 'module avail'
            # subProc=sp.Popen(cmd, shell=True, executable='/bin/bash', stdout=sp.PIPE, stderr=sp.STDOUT)
            # subProc.wait()
            # output = subProc.stdout.read()
        else:
            loadModule = False
            
        # to actually make a mp4:
        imgs = glob.glob(directory + '*' + picType)
        if len(imgs)>0: 
            baseName = os.path.basename(imgs[0])
            baseName = baseName.replace(baseName.split('_')[-1],'')
            if saveName==None: saveName=baseName[:-1]
            mp4Files = glob.glob(saveLoc + '*.mp4')
            Nmp4 = len(mp4Files)
            #print(baseName)
            if (Nmp4 > 0) and overwrite:
                for mp4File in mp4Files:
                    os.remove(mp4File) 
            if (Nmp4 == 0) or overwrite:
                frameRate = 5
                maxVideoTime = 120 # secons
                # calculate frameRate
                if (len(imgs)/frameRate) > maxVideoTime:
                    frameRate = len(imgs)/maxVideoTime
                
                command = []
                if loadModule: command.append('module load ffmpeg/5.0 && ')
                # command.append('ffmpeg -framerate ' + str(frameRate) + ' -i ' + directory + baseName + '%05d.jpeg -vcodec mpeg1video -r 24 ' + saveLoc+saveName + '.mp4')
                command.append('ffmpeg -framerate %i -start_number_range 1000 -i %s%s%%05d.%s -vcodec mpeg1video -r 24 %s%s.mp4'%(frameRate,directory,baseName,picType,saveLoc,saveName))
                cmd = ''.join(command)
                
                subProc=sp.Popen(cmd, shell=True, executable='/bin/bash', stdout=sp.PIPE, stderr=sp.STDOUT)
                subProc.wait()
                if False:
                    print('\n\n#########   FFMPG output begin  ############\n')
                    output = subProc.stdout.read()
                    print(output.decode('ascii'))
                    print('\n\n#########   FFMPG output end  ############\n')
                subProc.terminate()
            else:
                print('mp4 file already exists')
    #          sample command: "module load ffmpeg/5.0 && ffmpeg -framerate 5 -i electrons_%05d.jpeg -vcodec mpeg1video -r 24 electrons.mp4"
        else: print('No %s files exist in %s'%(picType,directory))
        return 0
            
def fix_eps(fileName):
    # there is a boundingbox error in the eps files. the %%BoundingBox parameters are saved as floats, which epspdf doesnt like
    # this code fixes that
    
    # 'gs -q -dBATCH -dNOPAUSE -sDEVICE=bbox /media***REMOVED***FLAIR/IRthermography/data/CeO2/sample1/date-8.12.20/tempSweepMiddle/processed/tempSweep_center_avg.eps'
    newBB = sp.run(['gs', '-dNOPAUSE', '-dBATCH', '-q', '-sDEVICE=bbox', fileName] , stdout=sp.PIPE,stderr=sp.PIPE)
    newBB = newBB.stderr.decode('utf-8')
    tempName = 'temp.eps'
    with open(fileName,'r') as epsfile, open(tempName, 'w') as temp_file:
        for line in epsfile:
            if '%%BoundingBox:' in line:
                temp_file.write(newBB)
            else:
                temp_file.write(line)
    shutil.move('./' + tempName, fileName)
    return


def get_windowed_info(y, x, win=None, overlap = 0.5, info='period', **kwargs):
    """
    Parameters
    ----------
    y : numpy array
        1D array representing the signal
    x : numpy array
        1D array representing the position
    win : scaler, optional
        This represents the windo size
    overlap : float, optional
        value can must be (0,1), and represents the overlap of the windows

    Returns
    -------
    Ts : numpy array
        array represents the periods of each window
    xs : numpy array
        array representing the new positions of the same length of Ts

    """
    if type(x) == type(None):
        pass
    dx = x[1]-x[0]
    if type(win) == type(None):
        win = len(y)
    elif  type(win) == int:  
        pass
    elif type(win) == float: 
        win = int(win/dx)
    
    hop_size = np.int32(np.floor(win * (1-overlap)))
    total_segments = np.int32(np.ceil(len(y) / np.float32(hop_size)))-1
    
    Is = np.empty((total_segments), dtype=np.float32)
    xs = np.empty((total_segments), dtype=np.float32)
    Isegment = x[0:win]
    for i in range(total_segments):                      # for each segment
        current_hop = hop_size * i                        # figure out the current segment offset
        Ysegment = y[current_hop:current_hop+win]  # get the current segment
        
        if info == 'period':
            Is[i] = get_period(Ysegment, Isegment, **kwargs)
        elif info == 'phase':
            Is[i] = get_phase(Ysegment, Isegment, **kwargs)
        xs[i] = x[current_hop + hop_size]
        
    # copy the first and last elements to fill the entire range
    if len(Is)>0:
        xs = np.concatenate([ [x[0]],xs,[x[-1]] ])
        Is = np.concatenate([ [Is[0]],Is,[Is[-1]] ])
    else: 
        xs = None
        Is = None
    return Is,xs


# def chunks(lst, n):
#     """Yield successive n-sized chunks from lst."""
#     for i in range(0, len(lst), n):
#         yield lst[i:i + n]

def chunks(lst, n):
    n = max(1, n)
    return (lst[i:i+n] for i in range(0, len(lst), n))

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))


if __name__ == "__main__":
    import dataDir
    folder = '/home***REMOVED***Documents/data/CFAdata/testData/'
    DD = dataDir.DataDir(folder)
    DF = DD.Fields.read_as_df('E', 1)
    DF = DD.DFM.getSlice(DF,'t',0)
    array,bounds = DD.DFM.df_to_numpy(DF)
    
    theCurl = curl(array)
    






