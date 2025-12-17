# -*- coding: utf-8 -*-
import tables as tb
from tables import StringCol,Int64Col,UInt16Col,UInt8Col,Int32Col,Float32Col,Float64Col,IsDescription
import pandas as pd
import numpy as np
import os


from dmanage.components import HardCache

def generate_data():
    # waveform parameters
    f = 2e3                     # frequency
    T = 1/f                       # Period
    t = np.linspace(0,10*T,1000)  # time vector, 10 periods
    voltage = np.sin(2*np.pi*f*t)
    data = np.stack([t,voltage]).T  
    data = pd.DataFrame(data,columns=['Time','Voltage'])   # create pandas dataframe
    data = data.set_index('Time')      
    return data




if __name__ == "__main__":
    # generate data
    wave = generate_data()

    filepath = "cache.h5"
    
    # if os.path.exists(filepath):
    #     os.remove(filepath)
    #h5file = tables.open_file(filepath, mode="w", title="Hard Cache")
    
    # save scalars
    # group = h5file.create_group("/", 'scalars', 'Scalars')
    # table = h5file.create_table(group, 'table',{'name':StringCol(32),'value':Float64Col()} , "Table of scalar and string variables")
    # row = table.row
    # for i in range(10):
    #     row['name'] = 'var%i'%i
    #     row['value'] = i
    #     row.append()
    # table.flush()  
    
    
    # save dataframes
    
    # df = generate_data()
    # df.to_hdf(filepath,key='/DataFrames/wave1000',format='table')
    
    
    
    # h5file.close()
    
    
    cache = HardCache(loc='./',name=filepath)
    #cache.open()
    cache.save(wave,'wave')
    cache.save(wave,'wave2')
    keys = cache.keys()
    print(keys)
    cache.remove('wave2')
    df = cache.get('wave')
    # cache.close()
    
    
    
    
    
    