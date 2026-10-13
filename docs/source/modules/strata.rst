
strata
------

This module provides the framework to convert ``DataUnit`` objects into ``DataGroup`` objects. The user creates a DataUnit object, and the ``make_data_group()`` method wraps methods decorated with ``override()`` with a parallel for loop that steps through all data units and applies the method. DataUnit objects require a ``unitType`` attribute and an ``is_valid`` method defined to use the DataGroup functionality. An example is shown below::

    from dmanage.strata import make_data_unit, make_data_group, override
    from dmanage import metastring

    DataUnit = make_data_unit(name='DataFile')
    class DataFile(DataUnit):
        unitType = 'file'    # REQUIRED, this class definition lets the DataGroup know the data type, 'file', 'dir', or 'test'
        
        def __init__(self,filepath):
            self.dataFile = filepath
        
        # REQUIRED, this checks if the data unit is valid data, invalid data is skipped in the DataGroup object
        def is_valid(self,dataFile):
            return ('.csv' in dataFile)
        
        # override instructs the DataDirectory class to override the method with parallelly 
        # looped method to step through each data unit
        @override()
        def read_waveform(self):
            df = pd.read_csv(self.dataFile)
            df = df.set_index('Time')
            return df
        
        # no override here because dmanage.metadata.parser.parse_filename concats the result where 
        def parse_filename(self):
            return parse(self.dataFile, 'Vin')
            
        @override()
        def get_waveform_rms(self):
            df = self.read_waveform()
            return np.sqrt((df['Voltage']**2).mean())


    DataDir = make_data_group(DataFile)    # This enables DataGroup functionality
    class DataDirectory(DataDir):
        """
        Data Directory class that reads all csv waveform files in a directory and gives access
        to wrapped DataFile class arrays. Each method in the DataFile class is wrapped with the
        parallelize_iterator_method to step through all detected waveform files

        The attribute self.dataUnits contains a list of all valid csv files
        """
        # This overrides the DataFile method and uses the DataDir self.dataUnits Parameter
        def parse_filename(self):
            return metastring.parse(self.dataUnits, 'Vin')  # We utilize the self.dataUnits attribute here instead

