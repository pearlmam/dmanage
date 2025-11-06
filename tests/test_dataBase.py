# -*- coding: utf-8 -*-



from dmanage import dfmethods as dfm
from dmanage.group import makeDataGroup # this needs to change to be more generic
from dmanage.unit import makeDataUnit  # this needs to change to be more generic
from dmanage.base import makeDataBase  # this needs to change to be more generic
from dmanage.plugins import vsim



DataDir = makeDataUnit(vsim.loader.VSim)
class MyDataDir(DataDir):
    def __init__(self,dataDir=None):
        super().__init__(dataDir)
        # add personal component loader here that modifies self Obj
        # personalSimulationLoader(dataDir,self)
        
        ####   add any attributes here    ####
        
    #### Add person methods here   ####
SweepDir = makeDataGroup(MyDataDir)
class MySweepDir(SweepDir):
    # def __init__(self,dataDir=None):
    #     #super().__init__(dataDir
    #     pass
    pass

DataBase = makeDataBase(MySweepDir)
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


