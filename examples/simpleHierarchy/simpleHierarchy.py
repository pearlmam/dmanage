# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import shutil
import os
import matplotlib.pyplot as plt
from pathlib import Path
import multiprocess as mp


from dmanage.group import make_data_group
from dmanage.unit import make_data_unit
from dmanage.decorate import override
from dmanage.metadata.metastring import parse
import dmanage.dfmethods as dfm

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
    f = 1e3                       # frequency
    T = 1/f                       # Period
    t = np.linspace(0,10*T,1000)  # time vector, 10 periods
    gain = 2                      # gain of the circuit (Vout/Vin)
    
    
    # delete the contents of the folder if it exists
    if os.path.exists(saveloc):
        shutil.rmtree(saveloc)  # this command fails if directory doesnt exist
    # create the save directory if it doesn't exist
    if not os.path.exists(saveloc):
        os.makedirs(saveloc)    # this command fails if the directory exists already
        
    Vins = np.linspace(1,10,10)
    for Vin in Vins:
        Vnew = Vin*np.sqrt(2)*gain*np.sin(2*np.pi*f*t)       # output voltage
        
        # save waveform
        savename = 'waveform_Vin-%0.1f.csv'%Vin   # save name defining Vin by the dmanage naming convention
        data = np.stack([t,Vnew]).T   # combine t and V into one 2D array, first col is t and second is V
        waveform = pd.DataFrame(data,columns=['Time','Voltage'])   # create pandas dataframe
        waveform.to_csv(saveloc+savename,index=False)              # save to a file
    return 

DataUnit = make_data_unit()
class DataFile(DataUnit):
    """
    This is where the waveform processing methods live. The waveform is the only 
    component of the DataUnit, so this implementation uses no components for simplicity.
    The @override decorators flag the method for DataGroup method wrapping. These
    methods will be overriden in the DataGroup class for steping through each dataUnit.
    """
    def __init__(self,filepath):
        self.dataUnit = filepath
        self.baseDir = os.path.join(os.path.dirname(filepath),'')
        self.resultDir = self.baseDir + 'processed/'
        self.Plot = dfm.plot.Plot()
        
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
    def read_waveform(self):
        df = pd.read_csv(self.dataUnit)
        df = df.set_index('Time')
        return df
    
    def parse_filename(self):
        """returns a dict of the 'Vin' and its value pair
        This utilizes the dmanage.metadata.metastring.parse function
        no override here because metastring.parse can take a list as an input
        This function will manually be overridden in the DataDirectory
        """
        return parse(self.dataUnit, 'Vin')
        
    @override()
    def get_waveform_rms(self):
        df = self.read_waveform()
        return np.sqrt((df['Voltage']**2).mean())
    
    @override('plot')
    def plot_waveform(self,savename,saveloc=None,fig=1):
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
        # print(mp.current_process())
        # pid = os.getpid()
        if saveloc is None:
           saveloc = self.resultDir
        if not os.path.exists(saveloc):
           os.makedirs(saveloc)
        savetag = self.savetag()
        df = self.read_waveform()
        fig,ax = self.Plot.plot1d(df,fig=fig)
        savename = savename + savetag + '.' + self.Plot.P.saveType
        fig.savefig(saveloc + savename, bbox_inches='tight', format=self.Plot.P.saveType)

DataDir = make_data_group(DataFile)
class DataDirectory(DataDir):
    # overrides the DataUnit method with one that can step through the dataUnits
    def parse_filename(self):
        return parse(self.dataUnits, 'Vin')
    pass


if __name__ == "__main__":
    # file inputs
    dataLoc = './test_data/'                # save location
    dataFile = 'waveform_Vin-1.0.csv'
    generate_data(dataLoc)             # generate data
    
    # process the data
    D = DataFile(dataLoc+dataFile)
    D.plot_waveform('waveform')       # plot one waveform to test
    
    DD = DataDirectory(dataLoc,dataUnitType='files')
    
    # read the input and output rms voltages
    Vrms = DD.get_waveform_rms()
    Vin = DD.parse_filename().to_numpy()
    
    # plot the sweep result
    fig = plt.figure(1, figsize=(8,3),clear=True)
    ax = fig.subplots(nrows=1,ncols=1)
    ax.plot(Vin,Vrms)
    
    # plot and save all the waveforms
    DD.plot_waveform('waveform',nc=4)
    
    # NOTE: using nc>1 utilizes a parallel implementation to save the plots,
    # sometimes this can cause data corruption if the processes are using the same figure
    # or the plotting backend is interactive. Set the backend to 'agg' and ensure that
    # each process uses there own figure for plotting.
    
    
    
    
    
    
    
    
    
    