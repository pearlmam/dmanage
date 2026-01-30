# -*- coding: utf-8 -*-

import testObjects
import warnings
import time
from dmanage.strata.components import ZarrCache, ParquetCache

warnings.filterwarnings("ignore",
    message="Consolidated metadata is currently not part",
    category=UserWarning)

zarrLoc = 'cache.zarr'
parquetLoc = 'cache.parq'

class TestHardCache:
    def __init__(self,cacheType,compression = "snappy",debug=False):
        self.cacheType = cacheType
        if cacheType == 'zarr':
            self.hardCache = ZarrCache(zarrLoc)
        else:
            compression = compression
            self.hardCache = ParquetCache(parquetLoc,compression=compression,debug=debug)
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
        thread = True
        size = 10000
        print("Writing and getting, wait to finish: thread = %s ..."%thread)
        startTime = time.time()
        dfs = []
        for i in range(0,N):
            dfs.append(DU.gen_DataFrame(i,size=size))
            self.hardCache.save(dfs[i],'dfLarge%d'%i,thread=thread)
        assert all(self.hardCache.get('dfLarge0') == dfs[0])
        assert all(self.hardCache.get('dfLarge1') == dfs[1])
        assert all(self.hardCache.get('dfLarge2') == dfs[2])  # this needs to wait
        self.hardCache.flush()
        executionTime = time.time() - startTime
        print("Done in %.2f seconds"%executionTime)
        
        
        print('###########################################')
        print("Writing and writing thread = %s ..."%thread)
        startTime = time.time()
        self.hardCache.save(dfs[2],'dfLarge2',thread=thread)  # write large file
        for i in range(0,N-1):
            self.hardCache.save(dfs[i],'dfLarge%d'%i,thread=thread)
        seriess = []
        for i in range(0,N):
            seriess.append(DU.gen_Series(i,size=size))
            self.hardCache.save(seriess[i],'seriesLarge%d'%i,thread=thread)
        self.hardCache.flush()
        executionTime = time.time() - startTime
        print("Done in %.2f seconds"%executionTime)
        
        
        print('###########################################')
        print("Writing and getting, no waiting thread = %s ..."%thread)
        startTime = time.time()
        dfs = []
        for i in range(0,N):
            dfs.append(DU.gen_DataFrame(i,size=size))
            self.hardCache.save(dfs[i],'dfLarge%d'%i,thread=thread)

        assert all(self.hardCache.get('seriesLarge0') == seriess[0])
        assert all(self.hardCache.get('seriesLarge1') == seriess[1])
        assert all(self.hardCache.get('seriesLarge2') == seriess[2])  # this needs to wait
        self.hardCache.flush()
        executionTime = time.time() - startTime
        print("Done in %.2f seconds"%executionTime)
        
if __name__ == "__main__":
    # Test = TestHardCache(cacheType='zarr')
    # Test.test_df_write_read()
    # Test.test_series_write_read()
    # Test.test_threading()
    
    Test = TestHardCache(cacheType='parquet',compression='snappy')
    Test.test_df_write_read()
    Test.test_series_write_read()
    Test.test_threading()
    
    
    
    
    
    # DU = testObjects.MyDataUnit()
    # hardCache = ParquetCache(parquetLoc)
    # n=2
    # df = DU.gen_DataFrame(n,size=10000)
    # hardCache.remove('dfLarge%d'%n)
    # hardCache._save(df,'dfLarge%d'%n)
    # hardCache._save(df,'dfLarge%d'%n)
    # print('after save')
    # time.sleep(.5)
    # hardCache.save(df,'dfLarge%d'%n,thread=False)
    
    # print(hardCache.get('dfLarge%d'%n))
    
    # for i in range(4):
    #     time.sleep(.5)
    #     print(hardCache.get('dfLarge%d'%n))
        
    
    
    
