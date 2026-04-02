# common packages

# necessary packages for data hierarchy
from dmanage.strata import make_data_group
from dataUnit import MyDataUnit

DataGroup = make_data_group(MyDataUnit)
class MyDataGroup(DataGroup):
    """this is a simple DataGroup class
    """
    def __init__(self,grouppath):
        """open the data group. super().__init__ checks the path for data units
        """
        unitType = 'file'  # options: 'file' or 'dir'
        super().__init__(grouppath, unitType=unitType)

if __name__ == "__main__":
    # group path
    grouppath = '/path/to/dataGroup'

    
    # instantiate the data group for testing group arrays
    DG = MyDataUnit(grouppath)
