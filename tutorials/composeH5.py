# -*- coding: utf-8 -*-
import tables
from tables import StringCol,Int64Col,UInt16Col,UInt8Col,Int32Col,Float32Col,Float64Col,IsDescription
import pandas as pd
import numpy as np
import os



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


class Particle(IsDescription):
    name      = StringCol(16)   # 16-character String
    idnumber  = Int64Col()      # Signed 64-bit integer
    ADCcount  = UInt16Col()     # Unsigned short integer
    TDCcount  = UInt8Col()      # unsigned byte
    grid_i    = Int32Col()      # 32-bit integer
    grid_j    = Int32Col()      # 32-bit integer
    pressure  = Float32Col()    # float  (single-precision)
    energy    = Float64Col()    # double (double-precision)




if __name__ == "__main__":
    # generate data
    wave = generate_data()
    
    filepath = "tutorial1.h5"
    
    if os.path.exists(filepath):
        os.remove(filepath)
    
    
    h5file = tables.open_file(filepath, mode="w", title="Test file")
    group = h5file.create_group("/", 'detector', 'Detector information')
    table = h5file.create_table(group, 'readout', Particle, "Readout example")
    particle = table.row
    for i in range(10):
        particle['name']  = f'Particle: {i:6d}'
        particle['TDCcount'] = i % 256
        particle['ADCcount'] = (i * 256) % (1 << 16)
        particle['grid_i'] = i
        particle['grid_j'] = 10 - i
        particle['pressure'] = float(i*i)
        particle['energy'] = float(particle['pressure'] ** 4)
        particle['idnumber'] = i * (2 ** 34)
        # Insert a new particle record
        particle.append()
    
    
    table.attrs.gath_date = "Wed, 06/12/2003 18:33"
    table.attrs.temperature = 18.4
    table.attrs.temp_scale = "Celsius"
    detector = h5file.root.detector
    detector._v_attrs.stuff = [5, (2.3, 4.5), "Integer and tuple"]
    
    table.flush()
    
    pressure = [ x['pressure'] for x in table.where("""(TDCcount > 3) & (20 <= pressure) & (pressure < 50)""") ]
    names = [ x['name'] for x in table.where("""(TDCcount > 3) & (20 <= pressure) & (pressure < 50)""") ]
    
    
    
    # create new array
    gcolumns = h5file.create_group(h5file.root, "columns", "Pressure and Name")
    h5file.create_array(gcolumns, 'pressure', np.array(pressure), "Pressure column selection")
    h5file.create_array(gcolumns, 'name', names, "Name column selection")
    
    
    
    
    #h5file.close()
    
    