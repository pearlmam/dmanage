# common packages

# necessary packages for data hierarchy
from dmanage.strata import make_data_unit

DataUnit = make_data_unit()
class MyDataUnit(DataUnit):
    """this is a simple DataUnit class
    """
    def __init__(self,unitpath):
        """open the data unit
        """
        self.dataUnit = unitpath
        
    def is_valid(self,dataUnit):
        """returns bool if the unit is a valid data unit. 
        
        the DataGroup.__init__() method uses this to check if the file or 
        directory is valid. This method MUST have one input.
        
        Parameters
        ----------
        dataUnit : path to the dataunit
        """
        # enter validity check code here
        return True
  
if __name__ == "__main__":
    # unit paths
    unitpath = '/path/to/dataUnit'
    
    # instantiate the data unit for testing unit arrays
    DU = MyDataUnit(unitpath)
  
