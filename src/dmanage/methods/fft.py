import numpy as np
def fft(y, x, axis=-1, upsample=False, window='hanning'):
    """
    Applies the FFT along the last axis

    Parameters
    ----------
    y : TYPE
        DESCRIPTION.
    x : TYPE
        DESCRIPTION.
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
