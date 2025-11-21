#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  4 12:16:40 2022

@author: marcus
"""


def check_exist(diaNames, types, output=False):
    if not type(diaNames) is list: diaNames = [diaNames]
    for diaName in diaNames:
        if not diaName in types:
            if output: print('%s is not availiable'%(diaName))
            return False
            #if output: print('%s is availiable'%(diaName))
    return True


import glob
import subprocess as sp
import os
import matplotlib.pyplot as plt
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



from scipy import signal
import numpy as np
from scipy.spatial.transform import Rotation as R

def vrrotvec(a,b):
    """
    Determine the rotation vector from 2 vectors
    
    """
    if np.array_equal(a,b):
        axis = a
        angle = 0
    else:
        axis = np.cross(a,b)/np.linalg.norm(np.cross(a,b))
        angle = np.arccos(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))
    r = R.from_rotvec(angle * axis).as_matrix()
    return r


def mov_avg(array, n=3):
    # old 1D method
    # ret = np.cumsum(array, dtype=float)
    # ret[n:] = ret[n:] - ret[:-n]
    # return ret[n - 1:] / n
    # new ND method but it loses one extra point
    s = array.shape
    axis = len(s)-1
    ret = np.cumsum(array, dtype=float,axis=axis)
    return (np.take(ret,range(n,s[-1]),axis=axis) - np.take(ret,range(0,s[-1]-n),axis=axis))/n



def get_phase(y, x=None, refSignal='cos', period=None, hRatio=0.4, pRatio=0.3, debug=False, fignum=1):

    if type(period) == type(None):
        period = get_period(y=y, x=x, hRatio=hRatio, pRatio=pRatio)
    if type(x) == type(None):
        x = np.arange(0,len(y))
        
    if type(refSignal) is str:
        # yOffset = 0
        
        # generate sinusoid
        if 'abs' in refSignal:
            absoluteValue = True
            refSignal = refSignal.replace('abs(','')
            refSignal = refSignal.replace(')','')
        else:
            absoluteValue = False
        signalType = ''.join([char for char in refSignal if char.isalpha()])
        power = ''.join([char for char in refSignal if char.isdigit()])
        if power == '': 
            power = 1
        else:
            power = float(power)
        w = (power%2+1)*np.pi/period # either 2*pi*w for odd, pi*w for even
        if signalType.lower() == 'cos':
            ySignal = np.cos(w*x)**power
        if signalType.lower() == 'sin':
            ySignal = np.sin(w*x)**power   
        
        if absoluteValue:
            ySignal = np.maximum(ySignal,0) # This preserves the period
            
        # if refSignal == 'sin':  ySignal = np.cos(2*np.pi/period*x)
        # if refSignal == 'cos':  ySignal = np.cos(2*np.pi/period*x)
        # if refSignal == 'cos2':  ySignal = np.cos(np.pi/period*x)**2
        # if refSignal == 'cos10':  ySignal = np.cos(np.pi/period*x)**10
    else:
        ySignal = refSignal
        w = 2*np.pi/period # either 2*pi*w for odd, pi*w for even
    # if yOffset == 0:
    #     y = y - y.mean()
    out = signal.convolve(y,ySignal[-1::-1],mode='full')
    xMin = np.min(x)
    
    
    # xcorr = np.concatenate((-x[-1:0:-1],x))
    
    ##### method using half signal convolve
    # xcorr = x
    # out = out[-len(y):]
    # pks = signal.find_peaks(out,height = 0.5*np.max(out), prominence=0.5*np.max(out))
    # if len(pks[0])>0:
    #     iMax = pks[0][0]
    #     phi = xcorr[iMax]-xMin   # absolute shift
    # else:
    #     phi = np.nan
        
    ####### alternative method with full signal convolve 
    xCentered = x - xMin
    xcorr = np.concatenate((-(xCentered)[-1:0:-1],xCentered))
    iMax = np.argmax(out)
    
    if (out.max() - out.min()) > (abs(out.max())*0.5):
        # this condition confirms that the calculated phase is meaningful
        phi = xcorr[iMax]
    else:
        phi = np.nan
    
    
    # phi = xcorr[iMax]-xMin   # absolute shift
    
    if debug:
        if type(refSignal) is str:
            if signalType.lower() == 'cos':
                ySignalOver = np.cos(w*(x-phi))**power
            if signalType.lower() == 'sin':
                ySignalOver = np.sin(w*(x-phi))**power 
            xOver = x
            if absoluteValue:
                ySignalOver = np.maximum(ySignalOver,0) # This preserves the period
        else:
            ySignalOver = ySignal
            # xOver = x+(phi*w)%np.pi
            xOver = x+phi
            
        pks = signal.find_peaks(out,height = 0.5*np.max(out), prominence=0.5*np.max(out))
        fig = plt.figure(fignum, figsize=(12,5))
        fig.clear()
        ax = fig.subplots()
        ax.plot(x,ySignal,color='r',label='ref signal')
        
        ax.plot(x,y/(np.max(y)-np.min(y)),color='b',label='signal')
        
        ax.plot(xOver,ySignalOver,color='m',label='synced signal')
        # ax.set(xlim=[5e-8,10e-8])
        ax.legend(loc='best')
        fig.canvas.draw()
        fig = plt.figure(fignum+1, figsize=(12,5))
        fig.clear()
        ax = fig.subplots()
        ax.plot(xcorr,out)
        ax.scatter(xcorr[pks[0]],pks[1]['peak_heights'])
        fig.canvas.draw()
        dummy = 1
    return phi*2*np.pi/period
    # return phi
    
    

def get_period(y, x=None, hRatio=0.5, pRatio=0.5, window=None, periodicPad=False, method='xcorr', strictCheck=False, debug=False, fignum=1):
    """
    get the period of a signal y

    Parameters
    ----------
   
    y : numpy array
        one dimensional array representing the periodic signal
    x : numpy array
        one dimensional array representing the periodic signals position
        
        Returns
    -------
    T : float
        if x is defined, T represents the period
        if x is not defined, T represents the index of the period

    """
    
    y = y - y.mean()
    
    if method == 'xcorr':
        
        if window == 'hanning':
            window = np.hanning(len(y))
            y = y * window
        if periodicPad:
            ypad = np.concatenate([y[1:],y,y[:-1]])
            out = signal.convolve(ypad,y[-1::-1],mode='valid')
        else:
            out = signal.convolve(y,y[-1::-1],mode='full')
        
        usexout =True
        
        # check peaks to determine proper input parameters
        # pks = signal.find_peaks(out,height=np.min(out), prominence=0)
        # if len(pks[0])>1:
        #     topTwo = np.sort(pks[1]['peak_heights'])[-2:]
        #     np.diff(topTwo)[0]/topTwo[-1]
        # pks[1]['prominences']
        
        if not type(pRatio) is type(None): prominence = pRatio*(np.max(out)-np.min(out))
        else: prominence = 0
        if not type(hRatio) is type(None): height = hRatio*(np.max(out)-np.min(out)) + np.min(out)
        else: height = np.min(out)
        foundPeaks = False
    
        i = 0
        maxIt = 20
        while (not foundPeaks) and (i < maxIt):
            pks = signal.find_peaks(out,height=height, prominence=prominence)
            if len(pks[0])>1:
                # check for missed correlation peaks???
                
                foundPeaks = True
            else:
                if not type(pRatio) is type(None): 
                    pRatio = pRatio*0.9
                    prominence = pRatio*(np.max(out)-np.min(out))
                if not type(hRatio) is type(None): 
                    hRatio = hRatio*0.9
                    height = hRatio*(np.max(out)-np.min(out)) + np.min(out)
                if (type(pRatio) is type(None)) and type(hRatio) is type(None):
                    foundPeaks = True
                    
                    
            if debug:
                # fig = plt.figure(1, figsize=(12,5))
                # fig.clear()
                # ax = fig.subplots()
                # ax.plot(xcorr,out)
                # ax.scatter(xcorr[pks[0]],pks[1]['peak_heights'],color='b')
                # fig.canvas.draw()
                
                fig = plt.figure(fignum, figsize=(12,5))
                fig.clear()
                ax = fig.subplots()
                
                if usexout:
                    xout = np.cumsum(np.diff(x))
                    xout = np.concatenate([-xout[-1::-1], np.array([0]),xout])
                    ax.plot(xout,out)
                    ax.scatter(xout[pks[0]],pks[1]['peak_heights'],color='b')
                else:
                    ax.plot(out)
                    ax.scatter(pks[0],pks[1]['peak_heights'],color='b')
                fig.canvas.draw()
                
                fig = plt.figure(fignum+1, figsize=(12,5))
                fig.clear()
                ax = fig.subplots()
                ax.plot(x,y)
                fig.canvas.draw()
            i += 1
            
        if type(x) == type(None):
            T = np.mean(np.diff(pks[0]))
        else:
            # if len(x) != len(y):
            #     raise Exception('Length of x must equal length of y')
            # else:
            x=x-np.min(x)
            xcorr = np.concatenate((-x[-1:0:-1],x))
            if len(pks[0])>1:
                T = np.mean(np.diff(xcorr[pks[0]]))
            else:
                T=np.nan
            
                
            if str(T) == 'nan' and strictCheck:
                raise Exception('getPeriod() could not determine the period of the signal, there may not be enough periods in the window')
            
            
    else:
        if not type(pRatio) is type(None): prominence = pRatio*(np.max(y)-np.min(y))
        else: prominence = 0
        if not type(hRatio) is type(None): height = hRatio*(np.max(y)-np.min(y)) + np.min(y)
        else: height = np.min(y)
        foundPeaks = False

        pks = signal.find_peaks(y,height=height, prominence=prominence)
        xPeaks = x[pks[0]]
        if periodicPad and len(xPeaks)>0:
            xPeaks = np.append(xPeaks,  x[-1]+xPeaks[0])
        diffs = np.diff(xPeaks)
        T = diffs.mean()
 
            
    return T 

def get_windowed_fft(y, x, win=None, overlap = 0.5):
    if type(x) == type(None):
        pass
    dx = x[1]-x[0]
    if type(win) == type(None):
        win = len(y)
    elif  type(win) == int:  
        pass
    elif type(win) == float: 
        win = int(win/dx)
    
    fft_size = win
    
    
    hop_size = np.int32(np.floor(fft_size * (1-overlap)))
    pad_end_size = fft_size          # the last segment can overlap the end of the data array by no more than one window size
    total_segments = np.int32(np.ceil(len(y) / np.float32(hop_size)))-1
     
    window = np.hanning(fft_size)  # our half cosine window
    inner_pad = np.zeros(fft_size) # the zeros which will be used to double each segment size
     
    proc = np.concatenate((y, np.zeros(pad_end_size)))              # the data to process
    result = np.empty((total_segments, fft_size), dtype=np.float32)    # space to hold the result
    x = np.linspace(0,np.max(x),total_segments)
    freq = np.fft.fftfreq(fft_size*2,d=dx)[:fft_size]
    
    for i in range(total_segments):                      # for each segment
        current_hop = hop_size * i                        # figure out the current segment offset
        segment = proc[current_hop:current_hop+fft_size]  # get the current segment
        windowed = segment * window                       # multiply by the half cosine function
        windowed = windowed-np.mean(windowed)             # remove DC
        padded = np.append(windowed, inner_pad)           # add 0s to double the length of the data
        spectrum = np.fft.fft(padded) / fft_size          # take the Fourier Transform and scale by the number of samples
        autopower = np.abs(spectrum * np.conj(spectrum))  # find the autopower spectrum
        result[i, :] = autopower[:fft_size]               # append to the results array
        
    return result,freq,x


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
    
def get_windowed_period(y, x, win=None, overlap = 0.5, window='hanning'):
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
    
    Ts = np.empty((total_segments), dtype=np.float32)
    xs = np.empty((total_segments), dtype=np.float32)
    Tsegment = x[0:win]
    for i in range(total_segments):                      # for each segment
        current_hop = hop_size * i                        # figure out the current segment offset
        Ysegment = y[current_hop:current_hop+win]  # get the current segment
        
        Ts[i] = get_period(Ysegment, Tsegment, window=window)
        xs[i] = x[current_hop + hop_size]
        
    # copy the first and last elements to fill the entire range
    if len(Ts)>0:
        xs = np.concatenate([ [x[0]],xs,[x[-1]] ])
        Ts = np.concatenate([ [Ts[0]],Ts,[Ts[-1]] ])
    else: 
        xs = None
        Ts = None
    return Ts,xs

def find_peaks(x, y, hRatio=None, pRatio=None, tRatio=None, height=None, **kwargs):
    # find peaks
    if hRatio: height = hRatio*(np.nanmax(y) - np.nanmin(y)) + np.nanmin(y)
    else: height = height
    if pRatio: prom = pRatio*(np.nanmax(y) -np.nanmin(y)) 
    else: prom = pRatio
    if tRatio: thresh = tRatio*(np.nanmax(y) -np.nanmin(y)) 
    else: thresh = tRatio
    pks,props = signal.find_peaks(y,height=height, prominence=prom,threshold=thresh,**kwargs)
    props['widths'],_,_,_ = signal.peak_widths(y,pks)
    # print("widths = %s"%props['widths'])
    # print("peaks = %s"%pks)
    ypks = y[pks]
    xpks = x[pks]
    
    # organize frequency peaks by magnitude and display
    I = np.argsort(xpks) # [::-1]
    ypks = ypks[I]
    xpks = xpks[I]
    return xpks, ypks, props

def fft(y, x, axis=-1, upsample=False, window='hanning'):
    """
    Applies the FFT along the last axis

    Parameters
    ----------
    y : TYPE
        DESCRIPTION.
    x : TYPE
        DESCRIPTION.
    bounds : TYPE, optional
        DESCRIPTION. The default is [0.0,1.0].

    Returns
    -------
    freq : TYPE
        DESCRIPTION.
    A : TYPE
        DESCRIPTION.
    P : TYPE
        DESCRIPTION.

    """
    
    # s = y.shape
    # theRange=[0.0,1.0]
    # NSTART = int(s[axis]*theRange[0])
    # NEND = int(s[axis]*theRange[1])

    # y = np.take(y,range(NSTART,NEND),axis=axis)
    # x = x[NSTART:NEND]
    N = y.shape[axis]
    
    # organize data
    dx = x[1]-x[0]
    #fs = 1./dt
    # y = (y.T-np.mean(y,axis=axis)).T # remove DC offset
    ymean = np.array(np.mean(y,axis=axis))
    broadcastShape = list(ymean.shape)
    if axis < 0:
        pos = len(broadcastShape)+1 + axis
    else:
        pos=axis
    broadcastShape.insert(pos,1)
    
    ymean = np.reshape(ymean,broadcastShape)
    y = y-ymean
    
    # y = np.reshape(np.reshape(y,s[::-1],order='F')-np.mean(y,axis=axis),s,order='F') # remove DC offset
    # need to remove the DC offset in the axis direction
    
    if type(window) is str:
        if window.lower() == 'hanning':
            #### apply window
            dim_array = np.ones((1,y.ndim),int).ravel()
            dim_array[axis] = -1
            
            window = np.hanning(N)
            window = window.reshape(dim_array)
            
            y = y*window
    else:
        pass
    
    if upsample:
        padLength = N
        N = N + padLength
        y = np.pad(y, (0,padLength))
    
    
    
    # take FFT
    FFT = np.fft.fft(y,axis=axis)
    freq = np.fft.fftfreq(N,d=dx)
    
    # sort FFT from negative to positive
    I=np.argsort(freq)
    freq = freq[I]
    FFT = np.take(FFT,I,axis=axis)
    
    # remove negative frequencies
    I = freq >= 0
    freq = freq[I]
    FFT = np.take(FFT,np.where(I)[0],axis=axis)
    
    A = np.abs(FFT)
    A = A/np.nanmax(A)   # "normalize"
    P = np.angle(FFT)
    return freq,FFT
    # return freq,A,P

def fft2d(a, dxy=None):
    a = a-np.mean(a) # remove DC offset
    ft = np.fft.ifftshift(a)
    ft = np.fft.fft2(ft)
    ft = np.fft.fftshift(ft)
    s = ft.shape
    
    
    x = np.fft.fftfreq(s[0],d=dxy[0])
    y = np.fft.fftfreq(s[1],d=dxy[1])
    x.sort()
    y.sort()
    # x = np.arange(-s[0]/2.,s[0]/2.,1)+.5   
    # y = np.arange(-s[1]/2.,s[1]/2.,1)+.5
    # if not type(dxy) is None:
    #     x = x*dxy[0]
    #     y = y*dxy[1]
    return ft,x,y

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


def butter_highpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype = "high", analog = False)
    return b, a

def butter_highpass_filter(data, cutoff, fs, order=5):
    b, a = butter_highpass(cutoff, fs, order=order)
    y = signal.filtfilt(b, a, data)
    return y

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = signal.butter(order, normal_cutoff, btype = "low", analog = False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = signal.filtfilt(b, a, data)
    return y

def butter_bandpass(lowcut, highcut, fs, order=5):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        sos = signal.butter(order, [low, high], analog=False, btype='band', output='sos')
        return sos

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
        sos = butter_bandpass(lowcut, highcut, fs, order=order)
        y = signal.sosfilt(sos, data)
        return y

def curl(array,dsteps=None):
    s = array.shape
    if type(dsteps) == type(None): 
        dsteps = tuple([1]*(len(s)-1))
    elif type(dsteps) is list: tuple(dsteps)
    # keys = 'ABCDE'
    # dstepsDict = {}
    # for i,dstep in enumerate(dsteps):
    #     dstepsDict[keys[i]]=dstep
        
    #axis=tuple(np.arange(0,len(s)-1))
    grads = np.gradient(array,*dsteps,axis=tuple(np.arange(0,len(s)-1)))
    
    if len(s) == 4:
        curl = np.zeros(s)
        curl[:,:,:,0] = grads[1][:,:,:,2]-grads[2][:,:,:,1]
        curl[:,:,:,1] = grads[2][:,:,:,0]-grads[0][:,:,:,2]
        curl[:,:,:,2] = grads[0][:,:,:,1]-grads[1][:,:,:,0]
        
    if len(s) == 3:
        curl = np.zeros(s[:-1])
        curl = grads[0][:,:,1]-grads[1][:,:,0]
    return curl
    
if __name__ == "__main__":
    import dataDir
    folder = '/home***REMOVED***Documents/data/CFAdata/testData/'
    DD = dataDir.DataDir(folder)
    DF = DD.Fields.read_as_df('E', 1)
    DF = DD.DFM.getSlice(DF,'t',0)
    array,bounds = DD.DFM.df_to_numpy(DF)
    
    theCurl = curl(array)
    






