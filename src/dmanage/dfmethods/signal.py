# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import copy
from scipy import signal
from scipy.optimize import curve_fit

import dmanage.methods.signal
from dmanage.dfmethods.convert import numpy_to_df,df_to_numpy
from dmanage.methods import functions as func
from dmanage.dfmethods.fft import fft, fft_amplitude
from dmanage.dfmethods import plot


def find_pks(DF, maxPks=20, hRatio=None, pRatio=None, tRatio=None, height=None, **kwargs):
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else:
            varName = DF.columns[0]
    else:
        varName = DF.name
    if len(DF.index.shape) > 1:
        raise Exception("DF must be 1D (only have 1 index level)")
    
    y,bounds = df_to_numpy(DF)
    iName = list(bounds.keys())[len(y.shape)-1]
    x = bounds[iName]
    
    xpks,ypks,props = dmanage.methods.signal.find_peaks(x, y, hRatio=hRatio, pRatio=pRatio, tRatio=tRatio, height=height, **kwargs)
    
    # shorten peak list to < maxPks
    if len(ypks)>maxPks:
        ypks = ypks[0:maxPks] # remove simulation time frequency
        xpks = xpks[0:maxPks] # remove simulation time frequency
        
    numbers = [str(i) for i in range(len(xpks))]
    numbers = np.array(numbers)
    out = np.stack([xpks,ypks])
    i = pd.Index(xpks,name = iName)
    peaksDF = pd.DataFrame(ypks, columns=[varName],index=i)
    return peaksDF,props
    
    # peaksDF = pd.DataFrame(out, columns=['Freq\n[GHz]','Amp\n[arb]'])
    
    #output = peaksDF.to_string(formatters={'Freq [GHz]':'{:,.2f}'.format,'Per [ns]':'{:,.2f}'.format, 'Amp':'{:,.2f}'.format})
    #output = tabulate(peaksDF,floatfmt=".2f",headers="keys",tablefmt="plain",numalign="left")



def windowed_period(DF, win=None, overlap=0.5, window='hanning', inverse=False):
    if not issubclass(type(DF), pd.core.series.Series): 
        if len(DF.columns)>1:
            raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else:
            name = DF.columns[0]
    else:
        name = DF.name
        
    if type(DF.index) == pd.core.indexes.multi.MultiIndex:
        iNames = DF.index.names
        if len(iNames)>1: raise Exception('Index must have only one level')
        
    array,bounds = df_to_numpy(DF)
    iName = list(bounds.keys())[len(array.shape)-1]
    x = bounds[iName]
    Ts,xs = dmanage.methods.signal.get_windowed_period(array, x, win=win, overlap = overlap, window=window)
    
    if inverse: 
        if type(Ts) !=type(None): Ts=1/Ts
        col = 'freq(%s)'%name
    else:
        col = 'per(%s)'%name
    DF = pd.DataFrame(Ts,index=xs,columns=[col])
    DF.index.name = iName
    return DF

def get_phase(DF, refSignal='cos', period=None, hRatio=0.4, pRatio=0.3, phiRange='2pi', debug=False, fignum=1):
    
    if not issubclass(type(DF), pd.core.frame.DataFrame): 
        DF = DF.to_frame()

    if type(DF.columns) is pd.core.indexes.multi.MultiIndex:
        theIndexName = DF.columns.names[-1]
    elif not type(DF.columns.name) is type(None):
        theIndexName = DF.columns.name
    else:
        theIndexName = 'diagnostic'
    phi = []
    cols = []
    for col in DF.columns:        
        array,bounds = df_to_numpy(DF[col])
        iName = list(bounds.keys())[len(array.shape)-1]
        x = bounds[iName]
        phi = phi + [dmanage.methods.signal.get_phase(array, x=x, refSignal=refSignal, period=period, hRatio=hRatio, pRatio=pRatio, debug=debug, fignum=fignum)]
        if type(col) is tuple:
            theCol = col[-1]
        else:
            theCol = col
        # theCol = col
        cols = cols + [theCol]
    # if len(DF.columns)==1:
    #     phi = phi[0]
    #     cols = cols[0]
    DF1 = pd.DataFrame(data = phi, index=cols)
    DF1.columns = ['phase']
    DF1.index.name = theIndexName
    # if len(DF1) == 1:
    #     DF1 = DF1.reset_index(drop=True)
    
    if phiRange == '2pi':
        DF1 = ((DF1+2*np.pi)%(2*np.pi))
    elif phiRange == '2pi/pi':
        DF1 = ((DF1+2*np.pi)%(2*np.pi))/np.pi
    elif phiRange == 'pi':
        DF1 = (DF1+np.pi)%(2*np.pi) - np.pi
    
    
    return DF1

def get_period(DF, hRatio=0.5, pRatio=0.5, window='hanning', periodicPad=False, strictCheck=False, debug=False):
    """
    get the period of a signal y

    Parameters
    ----------
   
    """
    if not issubclass(type(DF), pd.core.frame.DataFrame): 
        DF = DF.to_frame()
    DF = DF.dropna()
    T = []
    for col in DF.columns:
        array,bounds = df_to_numpy(DF[col])
        iName = list(bounds.keys())[len(array.shape)-1]
        x = bounds[iName]
        T = T + [dmanage.methods.signal.get_period(array, x=x, hRatio=hRatio, pRatio=pRatio, window=window, periodicPad=periodicPad, strictCheck=strictCheck, debug=debug)]
    if len(DF.columns)==1:
        T = T[0]    
    # DF = pd.DataFrame(T)
    return T

def get_skew_asymmetry(DF):
    DF = DF.dropna()
    DF = DF - DF.mean()

    denom = (DF**2).mean()**(3/2.)
    # skew = (data**3).mean()/data.std()**3
    skew = (DF**3).mean()/denom
    skew.name='skew'
    asym = (np.imag(signal.hilbert(DF,axis=0))**3).mean(axis=0)/denom
    asym.name = 'asym'
    return pd.concat([skew,asym],axis=1)
        
def get_signal_info(DF):
    info = get_skew_asymmetry(DF)
    DF = DF.dropna()
    DF = DF - DF.mean()
    info['rms'] = np.sqrt((DF**2).mean(axis=0))
    info['pp'] = DF.max()-DF.min()
    return info

def check_stability(DF, method='fft', debug=False, **kwargs):
    
    if 'fignum' in kwargs.keys():
            fignum = kwargs['fignum']
    else:
        fignum = 10
    

    if method == 'fft':
        """
        requires: noiseLevel, the noise level of signal in dB 20*log10(DF)
        optional: cutoff=[0,inf], cutoff frequencies to ignore
                 
                  
        """
        noiseLevel=None
        if 'noiseLevel' in kwargs.keys():
            noiseLevel = kwargs['noiseLevel']
        else:
            raise Exception("kwarg 'noiseLevel' is required for checkStability'")
        
        if 'cutoff' in kwargs.keys():
            cutoff = kwargs['cutoff']
            fHigh = cutoff[1]
            fLow = cutoff[0]
        else:
            fHigh=1e100
            fLow=0    
        DF = fft(DF, window='hanning')
        DF = fft_amplitude(DF)
        DF = 20*np.log10(DF)
        DF = DF.iloc[ (DF.index.get_level_values(0)>=fLow) & (DF.index.get_level_values(0)<=fHigh) ]
        DFpks,props = find_pks(DF, maxPks=10, hRatio=None, pRatio=0.05, height=noiseLevel)
        if debug:
            fig,ax = plot.plot1d_pks(fig=fignum, pRatio=0.05, height=noiseLevel)
        Npks = len(DFpks)
        NpksCheck = 1
        if Npks == NpksCheck:
            stableFFT = True
        else:
            stableFFT = False
        stable = stableFFT
    
    if method == 'powerRing':
        """
        requires: cutoff, a list of the cutoff frequencies
        optional: filt=bandpass, the filter type
                  hRatio=None, height ratio of peak finder
                  pRatio=None, prominance of peak finder
                  
        """
        #### required
        if 'cutoff' in kwargs.keys():
            cutoff = kwargs['cutoff']
        else:
            raise Exception("kwarg 'cutoff' is required for checkStability of method '%s'"%(method))
        
        ##### Optional
        if 'filt' in kwargs.keys():
            filt = kwargs['filt']
        else:
            filt='bandpass'
        if 'hRatio' in kwargs.keys():
            hRatio = kwargs['hRatio']
        else:
            hRatio=None
        if 'pRatio' in kwargs.keys():
            pRatio = kwargs['pRatio']
        else:
            pRatio=None
        
        ###### filter check: check for oscillations
        NpksCheck = 0
        if filt.lower() == 'highlow':
            flow = min(cutoff)
            fhigh = max(cutoff)
            DFfilt = apply_filter(DF, method='high', cutoff=flow, order=3, axis=-1)
            if debug: 
                fig,ax = plot.plot1d(fig=fignum)
                fignum = fignum + 1
            DFfilt = apply_filter(DFfilt, method='low', cutoff=fhigh, order=3, axis=-1)
        elif filt.lower() == 'bandpass':
            flow = min(cutoff)
            fhigh = max(cutoff)
            DFfilt = apply_filter(DF, method='band', cutoff=cutoff, order=3, axis=-1)
            NpksCheck = 1
        elif filt.lower() == 'lowdiff':
            fhigh = max(cutoff)
            DFfilt = apply_filter(DF, method='low', cutoff=fhigh, order=3, axis=-1)
            if debug: 
                fig,ax = plot.plot1d(fig=fignum)
                fignum = fignum + 1
            DFfilt = DFfilt.diff()
        elif method.lower() == 'abs':
            DFfilt = DF.abs()
            
        else:
            DFfilt = copy.deepcopy(DF)

        DFpks,props = find_pks(DFfilt, maxPks=10, hRatio=hRatio, pRatio=pRatio)
        
        Npks = len(DFpks)
        stable = False
        if Npks == NpksCheck:
            stableFilt = True
        else:
            stableFilt = False
                
        if debug: 
            fig,ax = plot.plot1d(fig=fignum)
            fig,ax = plot.scatter(fig=fig, clear=False, color='b')
            ax.relim()
            ax.autoscale()
            ax.set(title='Peak Check: detect=%0.0f, max=%0.0f, stable = %0.0f'%(Npks,NpksCheck,stableFilt))
            fig = plot.draw_fig()
            fignum = fignum + 1
        stable = stableFilt
        
        
        # if decayCheck and not stable:
        
    if method == 'powerRingDecay':
        """
        requires: cutoff, a list of the cutoff frequencies
        optional: startupBuff=7e-9, the time after startup to check decay
                  minPks=3, the minimum numbewr of peaks to determine decay
                  
        """
        
        #### required
        if 'cutoff' in kwargs.keys():
            cutoff = kwargs['cutoff']
            flow = cutoff[0]
            fhigh = cutoff[1]
        else:
            raise Exception("kwarg 'cutoff' is required for checkStability of method '%s'"%(method))
            
        ##### Optional
        if 'startupBuff' in kwargs.keys():
            startupBuff = kwargs['startupBuff']
        else:
            startupBuff=10e-9
        if 'minPks' in kwargs.keys():
            minPks  = kwargs['minPks ']
        else:
            minPks = 3
          
        ######### begin method
        tStart = get_startup(DF, method='bandpass', cutoff=cutoff, hRatio=0.4, pRatio=0.4, debug=debug, fignum=fignum)
        
        if debug:
            fig,ax = plot.plot1d(fig=fignum)
            ax.set(title='Original Signal, tstart=%0.2f ns'%(tStart*1e9))
            fig = plot.draw_fig()
            fignum = fignum + 1

        #DF = applyFilter(DF,method='high',cutoff=flow,order=3,axis=-1)

        DFfilt = apply_filter(DF, method='low', cutoff=fhigh, order=3, axis=-1)
        if debug:
            fig,ax = plot.plot1d(fig=fignum)
            ax.set(title='low pass signal')
            fignum = fignum + 1
        
        DFfilt = DFfilt.loc[DFfilt.index.get_level_values(0)>(tStart+startupBuff)]
        DFfilt = DFfilt - DFfilt.mean()
        DFfilt = DFfilt.reset_index()
        # DFfilt['t'] = DFfilt['t'] - DFfilt['t'].min()
        DFfilt = DFfilt.set_index('t')
        DFfilt = DFfilt.abs()
        # DFfilt = DFfilt.pow(2)
        
        if debug:
            fig,ax = plot.plot1d(fig=fignum, clear=True)
        
        
        ###### step 2: check the decay of the beat signal
        # get as many peaks as i can?
        hRatio=None
        pRatio=0.1
        DFpksCheck,propsCheck = find_pks(DFfilt, maxPks=30, hRatio=hRatio, pRatio=pRatio)
        
        decayRate = np.nan
        ###### use curve fit on peaks, line
        if (DFpksCheck.shape[0] > minPks):
            
            firstPeak = DFpksCheck.iloc[0][0] # this is the first peak after the startup peak
            y = DFpksCheck[DFpksCheck.columns[0]].to_numpy()                # variable values need to be of similar order
            yNorm = 1/y.max()
            y = y*yNorm
            
            x = DFpksCheck.index.get_level_values(0).to_numpy()   # converted to ns to be similar in order
            xNorm = 1/x.max()
            x = x*xNorm
            curve,pcov = curve_fit(lambda x,m,b:line_equ(x, m, b), x, y)
            m,b = curve[0],curve[1]         # m [W/ns]
            decayRate = m*xNorm/yNorm/1e9     # [W/ns]
            decayRate = decayRate*yNorm     # [1/ns]
            
            # for sqared signal denormalization
            # m = np.sign(m)*np.sqrt(np.abs(m))
            # b = np.sign(b)*np.sqrt(np.abs(b))
            # yNorm =np.sqrt(yNorm)
            
            
            DFline = pd.DataFrame(line_equ(x, m, b) / yNorm, x / xNorm, columns=['decay fit'])
            DFline.index.name = 't'
            
            ###### minimum decay compensation for short times
            # need equation for minDecay that approaches minDecay for long times and something much higher for short times
            # equation of capacitor decay voltage.
            
            # this code should be implemented outside checkStable?
            tend = DFfilt.index.get_level_values(0).max() - DFfilt.index.get_level_values(0).min()
            tau = 5e-9
            alpha = 1/tau
            minDecay = 0.01
            maxDecay = 1
            minDecay = (maxDecay-minDecay)*np.exp(-alpha*tend)+minDecay

            if (decayRate <= -minDecay):
                stableDecay = True
            else:
                stableDecay = False
                
            if debug:
                # # for sqared signal denormalization
                # fig,ax = DFP.plot1D(DFfiltAbs,fig=fignum,clear=True)
                # fig,ax = DFP.DFP.plot.scatter(DFpksCheck.pow(1/2),fig=fig,clear=False,color='b')
                
                # for non-sqared signals
                fig,ax = plot.plot1d(fig=fignum, clear=True)
                fig,ax = plot.scatter(fig=fig, clear=False, color='b')
                
                fig,ax = plot.plot1d(fig=fig, clear=False)
                ax.relim()
                ax.autoscale()
                ax.set(title='mod decay [%%/ns]: detect=%0.1f, min=%0.1f, stable=%0.0f'%(-decayRate*100,minDecay*100,stableDecay))
                fig = plot.draw_fig()
                fignum = fignum + 1
        
        
        if method == 'powerDecay':
            maxAttenuationFactor = 0.03/10   # [1/ns]
            maxAttenuationRate = maxAttenuationFactor  # [1/ns]
            DFfilt = apply_filter(DF, method='low', cutoff=fhigh, order=3, axis=-1)
            tStart  = DFfilt.idxmax()[0]
            themax = DFfilt.max()[0]
            DFfilt = DFfilt[DFfilt.index.get_level_values(0) > tStart]
            
            if debug:
                fig,ax = plot.plot1d(fig=fignum)
                ax.set(title='Original Signal, tstart=%0.2f ns'%(tStart*1e9))
                fig = plot.draw_fig()
                fignum = fignum + 1
    
            
            #####  calculate slope to see linear attenuation of power

            # method 3: fitting a line to the profile itself
            y = DFfilt[DFfilt.columns[0]].to_numpy()                # variable values need to be of similar order
            x = DFfilt.index.get_level_values('t').to_numpy()*1e9   # converted to ns to be similar in order
            if len(y) > 0:
                curve,pcov = curve_fit(lambda x,m,b:line_equ(x, m, b), x, y)
                m,b = curve[0],curve[1]         # m [W/ns]
                attenuationRate = m/themax            # [1/ns]
                DFline = pd.DataFrame(line_equ(x, m, b), x / 1e9, columns=['fit'])
                DFline.index.name = 't'
                if -attenuationRate > maxAttenuationRate:
                    stableAttenuation = False
                else:
                    stableAttenuation = True

                if debug: 
                    fig,ax = plot.plot1d(fig=fignum)
                    fig,ax = plot.plot1d(fig=fig, clear=False)
                    ax.set(title='attenuation [%%/ns]: detect=%0.2f, min=%0.2f,stable=%0.0f'%(attenuationRate*100,-maxAttenuationRate*100,stableAttenuation))
                    fig = plot.draw_fig()
                    fignum = fignum + 1
            else:
                stableAttenuation = True
        stable = stableAttenuation
        
    return stable


def apply_filter(DF, method, cutoff, order=5, axis=-1, modLabels=True):
    '''
    methods = 'low', 'high', 'band'
    
    '''
    
    if not DF.isna().to_numpy().any():
        
        if not issubclass(type(DF), pd.core.series.Series): 
            if modLabels:
                cols = ['%sP(%s)'%(method[0].upper(),col) for col in DF.columns]
            else:
                cols = DF.columns
            if len(cols)>1:
                DF = DF.stack(dropna=False)
                
                #DF.name = 'value'
                if axis==-1: axis = axis-1
        else:
            if modLabels:
                cols = ['%sP(%s)'%(method[0].upper(),DF.name)]
            else:
                cols = [DF.name]
            
        if type(cutoff) is not list: cutoff = [cutoff]
        if method=='band':
            if len(cutoff) != 2:
                raise Exception('with method %s, cutoff must be a list of length 2'%method)
        else:
            if len(cutoff) != 1:
                raise Exception('with method %s, cutoff must be a scaler'%method)
            #cutoff = cutoff[0]
        
        
        array,bounds=df_to_numpy(DF)
        iName = list(bounds.keys())[axis]
        x = bounds[iName]
        
        dx=x[1]-x[0]
        fs = 1/dx
        nyq = 0.5 * fs
        normal_cutoff = [v/nyq for v in cutoff]
        if max(normal_cutoff)>1.0:
            raise Exception('maximum cutoff is higher than the Nyquist limit. Lower the high cutoff frequency.')
        padlen = None #int(array.shape[axis]*0.001)
        sos = signal.butter(order, normal_cutoff, btype=method, analog=False,output='sos')
        array = signal.sosfiltfilt(sos, array,axis=axis,padlen=padlen)
        # array = signal.sosfilt(sos, array,axis=axis)
        DF = numpy_to_df(array, bounds)
        if len(cols)>1: DF = DF.unstack()
        DF.columns = cols
    else:
        print('Could not filter signal because of NaN value!')
        DF = DF
        
    return DF


def get_beat_period(DF, cutoff=[50e6, 500e6], hRatio=0.4, pRatio=0.3, startup=True, debug=False):
    flow = 50e6
    fhigh = 500e6        
    startupBuff = 7e-9
    
    #DF = applyFilter(DF,method='high',cutoff=flow,order=3,axis=-1)
    if type(startup) is bool:
        startup = get_startup(DF, debug=False)
    elif type(startup) is float:
        pass
    else:
        startup = 0.0
            
    DF = apply_filter(DF, method='low', cutoff=fhigh, order=3, axis=-1)
    if debug:
        fig,ax = plot.plot1d(fig=11)
        ax.set(title='filtered signal')
    
    DF = DF.loc[DF.index.get_level_values('t')>(startup+startupBuff)]
    DF = DF - DF.mean()
    T = get_period(DF, hRatio=hRatio, pRatio=pRatio, debug=debug)
    if debug:
        fig,ax = plot.plot1d(fig=12)
        ax.set(title='Estimated Beat Period = %0.2f ns'%(T*1e9))

    return T

def get_startup(DF, method='bandpass', cutoff=[50e6, 500e6], hRatio=0.4, pRatio=0.4, debug=False, fignum=1):
    # requires output power signal
    if not type(cutoff) is list:
        cutoff = [cutoff]
    

    if method == 'highlow':
        flow = min(cutoff)
        fhigh = max(cutoff)
        DF = apply_filter(DF, method='high', cutoff=flow, order=3, axis=-1)
        if debug: plot.plot1d(fig=fignum)
        DF = apply_filter(DF, method='low', cutoff=fhigh, order=3, axis=-1)
    elif method == 'bandpass':
        flow = min(cutoff)
        fhigh = max(cutoff)
        DF = apply_filter(DF, method='band', cutoff=cutoff, order=3, axis=-1)
        if debug: plot.plot1d(fig=fignum)
    elif method == 'lowdiff':
        fhigh = max(cutoff)
        DF = apply_filter(DF, method='low', cutoff=fhigh, order=3, axis=-1)
        if debug: plot.plot1d(fig=fignum)
        DF = DF.diff()
    elif method == 'abs':
        DF = DF.abs()
        if debug: plot.plot1d(fig=fignum)
    else:
        if debug: plot.plot1d(fig=fignum)
        
    fignum += 1
    DFpks,props = find_pks(DF, maxPks=10, hRatio=hRatio, pRatio=pRatio)
    if debug: 
        fig,ax = plot.plot1d(fig=fignum)
        fig,ax = plot.scatter(fig=fig, clear=False, color='b')
        ax.relim()
        ax.autoscale()
        fig = plot.draw_fig()
    if not DFpks.empty: startup = DFpks.index[0]
    else: startup = np.nan
    return startup

def mov_avg(DF, n=100):
    DF = DF.rolling(n).mean()
    if not issubclass(type(DF), pd.core.series.Series): 
        DF.columns = ['movAvg(%s)'%col for col in DF.columns]
    else:
        DF.name = 'movAvg(%s)'%DF.name
    return DF.dropna()


  
def line_equ(x, m, b):
    #y=m*x+b
    return m*x+b

def exp_equ(x, m, b):
    #y=m*x+b  PLACEHOLDER, NOT ACCURATE
    return m*x+b

def sine_attenuation_equ(x, A, omega, phase, alpha):
    return A*np.exp(alpha*x)*np.sin(omega*x-phase)


