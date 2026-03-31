
import pandas as pd
import numpy as np
import shutil
import os
from pathlib import Path
import tables as tb
import copy

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

class HardCache():
    def __init__(self,loc='./processed/',name='cache.h5'):
        self.loc = loc
        self.name = name
        self.path = os.path.join(self.loc,self.name)
        self.h5file = type('Uninitialized', (object,), {'isopen':0})
        
    def open(self):
        """Open the Hard Cache h5 file
        
        This closes all the File objects already open on the Hard cache before 
        opening. This ensures there are no 'lost' File objects. Having an open
        File object may throw errors because 'it is already open'. Sometimes 
        re-opening an open File object will work in Python, sometimes not. Also,
        Other programs might not be able to open open File objects.
        """
        self.close()
        if not self.h5file.isopen:
            if os.path.exists(self.path):
                self.h5file = tb.open_file(self.path, mode="a")
            else:
                self.h5file = tb.open_file(self.path, mode="w",title='Hard Cache')
            
    def close(self):
        """close the h5 file
        
        This closes the h5 file if it has the File object. Sometimes if not closed
        properly and reopened, the FileRegistry has multiple instances of the File object. 
        The h5 file will appear closed and the object is 'lost'. If that is
        the case, this function searches the open h5 files in the FileRegistry,
        grabs the File object, and closes it.
        """
        openFiles = tb.file._open_files.get_handlers_by_name(self.path)
        if self.h5file.isopen:
            self.h5file.close()
        elif len(openFiles)>0:
            for openFile in copy.copy(openFiles):
                openFile.close()
            self.h5file = openFile

    def keys(self):
        """Gets the keys of the availiable data
        
        This walks through the groups and checks for leaves. Leaves are
        hanging nodes with no children; in other words, it's actual data.
        There could be a better way to do this, but I'm an amateur.
        
        Right now There are only DataFrames that can be stored in the 
        '/DataFrames' group. In the future I want to have scalars. And then these
        scalars can be combined with other DataUnits.
        """
        #groups = self.h5file.root._v_children.keys()
        keys = []
        if os.path.exists(self.path):
            self.open()
            for group in self.h5file.walk_groups():
                if bool(group._v_leaves.keys()):
                    keys = keys + [group._v_name]
        return keys
        
    def save(self,data,name):
        self.open()
        if isinstance(data,pd.core.frame.DataFrame):
            group = '/DataFrames/'+name
            data.to_hdf(self.path,key=group,mode='a',format='table')
        
    def remove(self,name):
        if os.path.exists(self.path): 
            self.open()
            if name in self.keys():
                group = '/DataFrames/'+name
                self.h5file.remove_node(group,recursive=True)
            else:
                raise Warning("No '%s' in Hard Cache, ignoring... Availiable keys: %s"%(name,self.keys()))
        else:
            raise Warning("No Hard Cache created, ignoring...")
    
    def delete_all(self):
        if os.path.exists(self.path):
            os.remove(self.path)
    
    def __del__(self):
        self.close()

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
        hardCacheName = 'cache' + self.saveTag() + '.h5'
        self.HardCache = HardCache(self.resultDir,hardCacheName)
        
        self.wavename = 'power'
        
    def is_valid(self,dataUnit):
        """returns bool if the file is a valid data file. 
        The '.csv' extension test could be more robust.
        """
        return ('.csv' in dataUnit)
    
    def savetag(self):
        """extract the metastring from the filename
        """
        filename = Path(self.dataUnit).stem
        return filename.split('_')[-1]
    
    @override()
    def read_waveform(self,cache=False):
        df = pd.read_csv(self.dataUnit)
        df = df.set_index('Time')
        if cache:
            self.Cache[self.wavename] = df
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
    
    cache = HardCache()
    cache.var1 = 45
   
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
    
    
    
    