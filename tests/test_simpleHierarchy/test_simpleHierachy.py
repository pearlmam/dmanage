# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import shutil
import os
import matplotlib.pyplot as plt

from dmanage.group import make_data_group
from dmanage.unit import make_data_unit
from dmanage.utils.utils import child_override
from dmanage.metadata.parser import parse_filename

def generateData(saveLoc):
    # waveform parameters
    f = 1e3                       # frequency
    T = 1/f                       # Period
    t = np.linspace(0,10*T,1000)  # time vector, 10 periods
    gain = 2                      # gain of the circuit (Vout/Vin)
    
    
    # delete the contents of the folder if it exists
    if os.path.exists(saveLoc):
        shutil.rmtree(saveLoc)  # this command fails if directory doesnt exist
    # create the save directory if it doesn't exist
    if not os.path.exists(saveLoc):
        os.makedirs(saveLoc)    # this command fails if the directory exists already
        
    Vins = np.linspace(1,10,10)
    for Vin in Vins:
        Vnew = Vin*np.sqrt(2)*gain*np.sin(2*np.pi*f*t)       # output voltage
        
        # save waveform
        saveName = 'waveform_Vin-%0.1f.csv'%Vin   # save name defining Vin by the dmanage naming convention
        data = np.stack([t,Vnew]).T   # combine t and V into one 2D array, first col is t and second is V
        waveform = pd.DataFrame(data,columns=['Time','Voltage'])   # create pandas dataframe
        waveform.to_csv(saveLoc+saveName,index=False)              # save to a file
    return 

DataUnit = make_data_unit()
class DataFile(DataUnit):
    def __init__(self,filepath):
        self.dataFile = filepath
    def isValid(self,dataFile):
        return ('.csv' in dataFile)
    
    @child_override
    def readWaveform(self):
        df = pd.read_csv(self.dataFile)
        return df
        
    @child_override    
    def parseFilename(self):
        return parse_filename(self.dataFile, 'Vin')
        
    @child_override
    def getWaveformRMS(self):
        df = self.readWaveform()
        return np.sqrt((df['Voltage']**2).mean())


DataDir = make_data_group(DataFile)
class DataDirectory(DataDir):
    pass

DataDir = make_data_group(DataFile)
class DataDirectory(DataDir):
    pass

if __name__ == "__main__":
    dataLoc = './test_data/'                # save location
    generateData(dataLoc)             # generate data

    
        
    DD = DataDirectory(dataLoc,dataUnitType='files')
    Vrms = DD.getWaveformRMS()
    Vin = DD.parseFilename()
    
    fig = plt.figure(1, figsize=(8,3))
    ax = fig.subplots(nrows=1,ncols=1)
    ax.plot(Vin,Vrms)
    
    
    
    
    
    
    