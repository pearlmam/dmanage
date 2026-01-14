"Refactoring" Data
==================

When you first start generating data, sometimes we name variables in a non-ideal way. You want to change the variable name, but you still need the old data. How do we change the name without breaking all the code we developed? Refactoring the actual data might be infeasible, so we apply a workaround in our processing code (hence why "refactoring" is in quotes). We generate a VarNames data structure class of all the relevant variable names, with a case statement to choose which naming scheme depending on the version. The DataUnit level checks the variable naming version, and instantiates the VarNames class as a DataUnit component! An example is below.

Example Data
------------

We have data that consists of input and output voltages and currents versus time in a csv file. ::

    Time,Vin,Vout,INPUT_CURRENT,OUTPUT_CURRENT
    0.00E+00,0.00E+00,0.00E+00,0.00E+00,0.00E+00
    1.00E-05,1.78E-01,4.27E-01,1.78E-04,4.27E-04
    2.00E-05,3.55E-01,8.52E-01,3.55E-04,8.52E-04
    3.00E-05,5.31E-01,1.27E+00,5.31E-04,1.27E-03
    4.00E-05,7.04E-01,1.69E+00,7.04E-04,1.69E-03
    5.01E-05,8.75E-01,2.10E+00,8.75E-04,2.10E-03
    6.01E-05,1.04E+00,2.50E+00,1.04E-03,2.50E-03
    7.01E-05,1.21E+00,2.89E+00,1.21E-03,2.89E-03
    8.01E-05,1.36E+00,3.27E+00,1.36E-03,3.27E-03
    9.01E-05,1.52E+00,3.64E+00,1.52E-03,3.64E-03
    1.00E-04,1.66E+00,3.99E+00,1.66E-03,3.99E-03
    1.10E-04,1.80E+00,4.33E+00,1.80E-03,4.33E-03
    1.20E-04,1.94E+00,4.65E+00,1.94E-03,4.65E-03
    1.30E-04,2.06E+00,4.95E+00,2.06E-03,4.95E-03
    1.40E-04,2.18E+00,5.23E+00,2.18E-03,5.23E-03
    1.50E-04,2.29E+00,5.50E+00,2.29E-03,5.50E-03
    1.60E-04,2.39E+00,5.74E+00,2.39E-03,5.74E-03
    1.70E-04,2.48E+00,5.95E+00,2.48E-03,5.95E-03
    1.80E-04,2.56E+00,6.15E+00,2.56E-03,6.15E-03
    1.90E-04,2.63E+00,6.31E+00,2.63E-03,6.31E-03
    2.00E-04,2.69E+00,6.46E+00,2.69E-03,6.46E-03

There are 5 columns. We are happy with the `Time`,`Vin`, and `Vout` headers, but we are unhappy with the 'INPUT_CURRENT' and 'OUTPUT_CURRENT' headers. We want to change these headers to 'Iin' and 'Iout' but we have already generated tons of data with these horrible naming scheme that doesn't work well with :ref:`Filenaming`. So, what do we do???


Process Data
-------------

We could attempt to actually refactor the data (changing the headers of every csv file), but sometimes this is infeasible. So we "refactor" our processing scheme. And that's what we do below. In this example we want to calculate the instantaneous input and output power of the DataUnit. To do this we must multiply voltages and currents and access them through the header. 

.. code-block:: python


    import pandas as pd
    import numpy as np
    
    class VarNames:
      def __init__(self,version):
        # these are good variable names
        self.Vin = 'Vin'
        self.Vout = 'Vout'

        if version == 1.0:
        # these are the names we wish to change
          self.Iin = 'INPUT_CURRENT'   
          self.Iout = 'OUTPUT_CURRENT'    
        else:
          # these are the new names
          self.Iin = 'Iin'
          self.Iout = 'Iout'
          
    class MyDataUnit:
      def __init__(self,filepath):
        self.dataFile = filepath
        df = self.readData()
        if 'INPUT_CURRENT' in df.columns:
          version = 1.0
        else:
          version = 1.1
        self.VN = VarNames(version)

      def readData(self):
        df = pd.read_csv(self.dataFile)
        df = df.set_index('Time')
        return df

      # old implementation   
      def ___getPower(self):
        # can only calculate power for old, dumb naming
        df = self.readData()
        Pin = df['Vin']*df['INPUT_CURRENT']
        Pout = df['Vout']*df['OUTPUT_CURRENT']
        power = pd.DataFrame(np.concatenate([[Pin,Pout]]).T,index=df.index)
        power.columns = ['Pin','Pout']
        return power
        
      def getPower(self):
        # can handle old and new naming
        df = self.readData()
        Pin = df[self.VN.Vin]*df[self.VN.Iin]
        Pout = df[self.VN.Vout]*df[self.VN.Iout]
        power = pd.DataFrame(np.concatenate([[Pin,Pout]]).T,index=df.index)
        power.columns = ['Pin','Pout']
        return power
         
In this implementation, instead of hard coding the header names, we setup a component ``self.VN`` of the DataUnit that contains all the variable names as attributes. The ``DataUnit.__init__()`` method checks which naming scheme it is, and passes that to our ``VarNames`` class. Now this DataUnit can handle old and new headers.

.. note::
   This version check must read the entire file to check the variable naming. And then to calculate the power, it must read the file again. This is inefficient. We might consider just reading the first line of the file to check the variable naming to be more efficient. 
         
         
