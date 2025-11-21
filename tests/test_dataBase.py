# -*- coding: utf-8 -*-



from dmanage import dfmethods as dfm
from dmanage.group import make_data_group # this needs to change to be more generic
from dmanage.unit import make_data_unit  # this needs to change to be more generic
from dmanage.base import make_database  # this needs to change to be more generic
from dmanage.plugins import vsim



DataDir = make_data_unit(vsim.loader.VSim)
class MyDataDir(DataDir):
    def __init__(self,dataDir=None):
        super().__init__(dataDir)
        # add personal component loader here that modifies self Obj
        # personalSimulationLoader(dataDir,self)
        
        ####   add any attributes here    ####
        
    #### Add person methods here   ####
SweepDir = make_data_group(MyDataDir)
class MySweepDir(SweepDir):
    # def __init__(self,dataDir=None):
    #     #super().__init__(dataDir
    #     pass
    pass

DataBase = make_database(MySweepDir)
class MyDataBase(DataBase):
    # def __init__(self,dataDir=None):
    #     #super().__init__(dataDir
    #     pass
    pass


if __name__ == "__main__":
    eceSim = '***REMOVED***.***REMOVED***.edu'
    eceSimFolders = ['/media***REMOVED******REMOVED***/Documents/CFAdata/2025/VBSweep/NXY-109/TEND-300e-9/FREQ-1.315e9/iCathode-1000/BSTATIC-0.140/PRF_AVG-200e3/']
    localFolder = ['./test_data/vsim_data/']
    dataBases = {eceSim:{'dataGroups':eceSimFolders,'user':'***REMOVED***'}, \
                 'local':{'dataGroups':localFolder,'user':'***REMOVED***'}}
    DB = DataBase(dataBases)


