# -*- coding: utf-8 -*-

import testObjects
import warnings
import zarr
import xarray as xr

from dmanage.components import HardCache

warnings.filterwarnings("ignore",
    message="Consolidated metadata is currently not part",
    category=UserWarning)

file = 'cache.zarr'

class TestHardCache:
    def test_df_write_read(self):
        DU = testObjects.MyDataUnit()
        hardCache = HardCache(file)
        N = 3
        # check DataFrames
        dfs = []
        for i in range(1,N+1):
            dfs.append(DU.gen_DataFrame(i))
            hardCache.save(dfs[i-1],'dfVariant%d'%i)
        for i in range(1,N+1):
            df = hardCache.get('dfVariant%d'%i)
            assert all(df == dfs[i-1])
    
    def test_series_write_read(self):
        DU = testObjects.MyDataUnit()
        hardCache = HardCache(file)
        N = 3
        # check Series
        dfs = []
        for i in range(1,N+1):
            dfs.append(DU.gen_Series(i))
            hardCache.save(dfs[i-1],'seriesVariant%d'%i)
        for i in range(1,N+1):
            df = hardCache.get('seriesVariant%d'%i)
            assert all(df == dfs[i-1])
        

if __name__ == "__main__":
    Test = TestHardCache()
    Test.test_df_write_read()
    Test.test_series_write_read()
    
    # DU = testObjects.MyDataUnit()
    # df = DU.gen_DataFrame(3)
    
    # xs = df.to_xarray()
    
    # xs.to_zarr("cache.zarr/df", mode="w")
    
    # xs2 = xr.open_zarr("cache.zarr/variant1")
    # df1 = xs2.to_dataframe()


    # root = zarr.open('cache.zarr',mode='r')