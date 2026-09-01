import numpy as np
from matplotlib import pyplot as plt
from scipy import signal


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
