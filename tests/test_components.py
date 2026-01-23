# -*- coding: utf-8 -*-

import testObjects
import warnings
import zarr
import xarray as xr
import time
from dmanage.components import ZarrCache, ParquetCache

warnings.filterwarnings("ignore",
    message="Consolidated metadata is currently not part",
    category=UserWarning)

zarrLoc = 'cache.zarr'
parquetLoc = 'cache.parq'

class TestHardCache:
    def __init__(self,cacheType,compression = "snappy"):
        self.cacheType = cacheType
        if cacheType == 'zarr':
            self.hardCache = ZarrCache(zarrLoc)
        else:
            compression = compression
            self.hardCache = ParquetCache(parquetLoc,compression=compression)
    def test_df_write_read(self):
        DU = testObjects.MyDataUnit()
        N = 3
        dfs = []
        for i in range(0,N):
            dfs.append(DU.gen_DataFrame(i))
            self.hardCache.save(dfs[i],'dfVariant%d'%i)
        for i in range(0,N):
            df = self.hardCache.get('dfVariant%d'%i)
            assert all(df == dfs[i])
    
    def test_series_write_read(self):
        DU = testObjects.MyDataUnit()
        N = 3
        dfs = []
        for i in range(0,N):
            dfs.append(DU.gen_Series(i))
            self.hardCache.save(dfs[i],'seriesVariant%d'%i)
        for i in range(0,N):
            df = self.hardCache.get('seriesVariant%d'%i)
            assert all(df == dfs[i])
            
    def test_threading(self):
        DU = testObjects.MyDataUnit()
        N = 3
        dfs = []
        startTime = time.time()
        thread = False
        print("Writing large files thread = %s ..."%thread)
        for i,j in enumerate(range(0,N)):
            dfs.append(DU.gen_DataFrame(j,size=10000))
            self.hardCache.save(dfs[i],'dfLarge%d'%i,thread=thread)
        
        print('  reading files while writing...', end = ' ' )
        assert all(self.hardCache.get('dfLarge0') == dfs[0])
        assert all(self.hardCache.get('dfLarge1') == dfs[1])
        print('Done')
        startTimeWait = time.time()
        print('  waiting for dfLarge2 to write...',end = ' ')
        assert all(self.hardCache.get('dfLarge2') == dfs[2])
        executionTime = time.time() - startTimeWait
        print("Done in %.2f seconds"%executionTime)
        
        
        
        for i,j in enumerate(range(0,N)):
            dfs.append(DU.gen_Series(j,size=10000))
            self.hardCache.save(dfs[i],'seriesLarge%d'%i,thread=thread)
        
        executionTime = time.time() - startTime
        print("Writing large files Done in %.2f seconds"%executionTime)
        
if __name__ == "__main__":
    Test = TestHardCache(cacheType='zarr')
    Test.test_df_write_read()
    Test.test_series_write_read()
    Test.test_threading()
    
    Test = TestHardCache(cacheType='parquet',compression="zstd" )
    Test.test_df_write_read()
    Test.test_series_write_read()
    Test.test_threading()
    
    
    
    
    
    # DU = testObjects.MyDataUnit()
    # hardCache = ParquetCache(parquetLoc)
    # n=3
    # df = DU.gen_DataFrame(n,size=10000)
    # hardCache.save(df,'dfLarge%d'%n,thread=True)
    # print('after save')
    # time.sleep(.5)
    # hardCache.save(df,'dfLarge%d'%n,thread=False)
    
    # print(hardCache.get('dfLarge%d'%n))
    
    # for i in range(4):
    #     time.sleep(.5)
    #     print(hardCache.get('dfLarge%d'%n))
        
    
    
    
