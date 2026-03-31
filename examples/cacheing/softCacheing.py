
import pandas as pd
import numpy as np
import shutil
import os
from pathlib import Path

# necessary packages for data hierarchy
from dmanage.strata.group import make_data_group
from dmanage.strata.unit import make_data_unit
from dmanage.strata.decorate import override
from dmanage.metadata import compose


def sineStep(t,risetime):
    return np.sin(0.5*np.pi*np.maximum(0.0,np.minimum(1.0,t/risetime)))**2

def generate_data(saveloc):
    """Generate example data for the project
    This generates 10 csv files with time and voltage columns. Each file is
    tagged with a metastring, the input voltage is labeled in the filename
    
    Parameters
    ----------
    saveLoc : string
        path to save the data.
    """
    
    # waveform parameters
    f = np.array([1e3,2e3])                      # frequency
    T = 1/f                       # Period
    t = np.linspace(0,50*max(T),10000)  # time vector, 10 periods
    N = 20  # number of data units
    # delete the contents of the folder if it exists
    if os.path.exists(saveloc):
        shutil.rmtree(saveloc)  # this command fails if directory doesnt exist
    # create the save directory if it doesn't exist
    if not os.path.exists(saveloc):
        os.makedirs(saveloc)    # this command fails if the directory exists already
        
    freqs = np.linspace(f[0],f[1],N)
    for freq in freqs:
        risetime = 10*T[0]
        delay = 10/freq*2
        gain = 20
        A = 1+(gain-1)*sineStep(t-delay,risetime)
        power = A*np.sin(2*np.pi*freq*t)**2       # output power
        # save waveform
        savetag = compose({'freq':'%0.2fe3'%(freq/1e3)})
        savename = 'waveform_%s.csv'%savetag   
        data = np.stack([t,power]).T  
        waveform = pd.DataFrame(data,columns=['Time','Power'])   # create pandas dataframe
        waveform.to_csv(saveloc+savename,index=False)            # save to a file
    return 

class SoftCache(dict):
    def __getattr__(self, key):
        if not key in self.keys():
            raise AttributeError("No '%s' in cache"%(key))
        return self[key]
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def __getitem__(self, key : str):
       if (not key in self.keys() and key[0] != '_'):
           raise KeyError("No '%s' in cache"%(key))
       return super().__getitem__(key)
   
    def __setitem__(self, key : str, value : all):
       return super().__setitem__(key, value)
   
    def get(self,key,method=None,*args,**kwargs):
        if (not key in self.keys()) and (method is not None):
            self[key] = method(*args, **kwargs)
        return self[key]

DataUnit = make_data_unit()
class MyDataUnit(DataUnit):
    """this is a simple DataUnit class
    """
    def __init__(self,filepath):
        """open the data unit
        """
        self.dataUnit = filepath
        self.baseDir = os.path.join(os.path.dirname(filepath),'')
        self.resultDir = self.baseDir + 'processed/'
        self.Cache = SoftCache()
        
        self.wavename = 'power'
        
    def is_valid(self,dataUnit):
        """returns bool if the file is a valid data file. 
        The '.csv' extension test could be more robust.
        """
        return ('.csv' in dataUnit)
    
    @override()
    def read_waveform(self,cache=False):
        df = pd.read_csv(self.dataUnit)
        df = df.set_index('Time')
        if cache:
            self.Cache[self.wavename] = df
        return df
    
    @override()
    def plot_waveform(self,saveloc=None,fig=1):
        """Plots and saves the waveform
        
        Parameters
        ----------
        savename : string
            This is the basename of the save string, the extension and a metastring 
            will be added.
        saveloc : string, optional
            the location to save the plots. If None is used, the save location will be 
            in self.resultDir. The default is None.
        """
        savename = 'power'
        if saveloc is None:
           saveloc = self.resultDir
        if not os.path.exists(saveloc):
           os.makedirs(saveloc)
        filename = Path(self.dataUnit).stem
        savetag = filename.split('_')[-1]
        df = self.read_waveform()
        fig,ax = plot.plot1d(df,fig=fig)
        savename = savename + savetag + '.' + plot.Defs.saveType
        fig.savefig(saveloc + savename, bbox_inches='tight', format=plot.Defs.saveType)
        
    @override()
    def get_startup(self,):
        # df = self.read_waveform()
        df = self.Cache.get(self.wavename,self.read_waveform,cache=True)
        tStart = dmanage.compute.backends.dfmethods.signal.get_startup(df, cutoff=[1e2, 5e4])
        self.Cache.tStart = tStart
        return tStart
    
    @override()
    def get_avg(self):
        if not 'tStart' in self.Cache.keys():
            self.get_startup()
        # df = self.read_waveform()
        df = self.Cache.get(self.wavename,self.read_waveform,cache=True)
        df = df.loc[df.index.get_level_values(0)>self.Cache.tStart]
        avg = df.mean().to_numpy()[0]
        return avg
    
    @override()
    def get_freq(self):
        if not hasattr(self.Cache,'tStart'):
            self.get_startup()
        #df = self.read_waveform()
        df = self.Cache.get(self.wavename,self.read_waveform,cache=True)
        df = df.loc[df.index.get_level_values(0)>self.Cache.tStart]
        fft = dmanage.compute.backends.dfmethods.fft.fft(df)
        A = dmanage.compute.backends.dfmethods.fft.fft_amplitude(fft)
        freq = A.idxmax().iloc[0]
        if isinstance(freq,tuple):
            # MultiIndex is a tuple, even if it only has one level
            # Index would not be a tuple and would cause an error
            freq = freq[0]
        return freq
    
    @override()
    def gen_summary(self):
        # this can utilize the cacheing in DataGroup implementation
        summary = {}
        summary['file'] = self.dataUnit
        summary['tStart'] = self.get_startup()
        summary['Pavg'] = self.get_avg()
        summary['freq'] = self.get_freq()
        # we use series here because key, value pairs correspond to index value pairs
        df = pd.Series(summary)  
        return df
        
DataGroup = make_data_group(MyDataUnit)
class MyDataGroup(DataGroup):
    """this is a simple DataGroup class
    """
    def __init__(self,grouppath):
        """open the data group. super().__init__ checks the path for data units
        """
        dataUnitType = 'file'  # options: 'file' or 'dir'
        super().__init__(grouppath,dataUnitType=dataUnitType)

def testCache(self,a,b=2):
    #print('testCache(%f, %f)'%(a,b))
    return a + b


if __name__ == "__main__":
    
    cache = SoftCache()
    cache.var1 = 45
    # three different ways to access the cache for this dict-like object
    print("cache.var1=%f \n"%(cache.var1) +
          "cache['var1']=%f \n"%cache['var1'] + 
          "getattr(cache,'var1')=%f \n"%getattr(cache,'var1') +
          "cache.get(var1)=%f \n" %cache.get('var1') + 
          "cache.get(var1,testCache,2,2)=%f \n"%cache.get('var1',testCache,2,2) +
          "cache.get(var2,testCache,2,2)=%f \n"%cache.get('var2',testCache,2,2))
    # cache.get('var3')
    # cache.clear()
    
    
    
    # # unit and group paths
    # folder = './test_data/'
    # filepath = folder + 'waveform_freq-1.00e3.csv'
    
    # generate_data(folder)
    
    # # instantiate the data unit for testing unit arrays
    # DU = MyDataUnit(filepath)
    
    # # test group arrays, this does  utilize the cache, because the DataUnit
    # # gets modified after every call...
    # tStart = DU.get_startup()
    # Pavg = DU.get_avg()
    # freq = DU.get_freq()
    # summary = DU.gen_summary()
    
    # # instantiate the data group for testing group arrays
    # DG = MyDataGroup(folder)
    # DG.plot_waveform()
    
    # # test group arrays, this does not actually utilize the cache, because
    # # the DataUnits get instantiated for each call...
    # startTime = time.time()
    # tStarts = DG.get_startup()
    # Pavgs = DG.get_avg()
    # freqs = DG.get_freq()
    # executionTime = time.time() - startTime
    # print('Not caching took %0.2f seconds'%executionTime)
    
    # startTime = time.time()
    # summary0 = DG.gen_summary()
    # summary1 = pd.concat(summary0,axis=1).T
    # executionTime = time.time() - startTime
    # print('Using caching took %0.2f seconds'%executionTime)
    
    # print(summary1)
    
    
    
    