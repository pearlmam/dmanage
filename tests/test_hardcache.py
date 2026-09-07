# -*- coding: utf-8 -*-
import importlib.util
import time
import warnings
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from dmanage.tools import JSONCache, ParquetCache, ZarrCache
from helpers.strata_objects import MyDataUnit

warnings.filterwarnings(
    "ignore",
    message="Consolidated metadata is currently not part",
    category=UserWarning,
)

# 1. Detect installed packages
HAS_ZARR = importlib.util.find_spec("zarr") is not None
HAS_PARQUET = (
    importlib.util.find_spec("pyarrow") is not None
    or importlib.util.find_spec("fastparquet") is not None
)

# 2. Fixtures for DataFrame-capable caches (Zarr & Parquet)
@pytest.fixture(
    params=[
        pytest.param(
            "zarr",
            marks=pytest.mark.skipif(not HAS_ZARR, reason="zarr not installed"),
        ),
        pytest.param(
            "parquet",
            marks=pytest.mark.skipif(
                not HAS_PARQUET, reason="pyarrow/fastparquet not installed"
            ),
        ),
    ]
)
def dataframe_cache(request, tmp_path):
    cache_type = request.param
    if cache_type == "zarr":
        return ZarrCache(str(tmp_path / "cache.zarr"))
    elif cache_type == "parquet":
        return ParquetCache(str(tmp_path / "cache.parq"), compression="snappy")

# 3. Fixture for JSON cache
@pytest.fixture
def json_cache(tmp_path):
    return JSONCache(str(tmp_path / "cache.json"))


class TestTabularCaches:
    def test_df_write_read(self, dataframe_cache):
        DU = MyDataUnit()
        N = 3
        dfs = [DU.gen_DataFrame(i) for i in range(N)]

        for i, df in enumerate(dfs):
            dataframe_cache.save(df, f"dfVariant{i}")

        for i, expected_df in enumerate(dfs):
            result_df = dataframe_cache.get(f"dfVariant{i}")
            # pd.testing or .equals handles DataFrame comparisons reliably
            assert_frame_equal(result_df, expected_df, check_names=False,check_dtype=False)

    def test_series_write_read(self, dataframe_cache):
        DU = MyDataUnit()
        N = 3
        series_list = [DU.gen_Series(i) for i in range(N)]

        for i, s in enumerate(series_list):
            dataframe_cache.save(s, f"seriesVariant{i}")

        for i, expected_s in enumerate(series_list):
            result_s = dataframe_cache.get(f"seriesVariant{i}")
            assert result_s.equals(expected_s)



    def test_threading(self, dataframe_cache):
        DU = MyDataUnit()
        N = 3
        size = 10000
        dfs = [DU.gen_DataFrame(i, size=size) for i in range(N)]
    
        for i, df in enumerate(dfs):
            dataframe_cache.save(df, f"dfLarge{i}", thread=True)
    
        # Ensure all background write threads complete before fetching
        dataframe_cache.flush()
    
        for i, expected_df in enumerate(dfs):
            result_df = dataframe_cache.get(f"dfLarge{i}")
            assert_frame_equal(
                result_df, 
                expected_df, 
                check_names=False, 
                check_dtype=False
            )


class TestJSONCache:
    def test_primitive_write_read(self, json_cache):
        N = 3
        for i in range(N):
            json_cache.save(i, f"primitiveVariant{i}")
        for i in range(N):
            assert json_cache.get(f"primitiveVariant{i}") == i

    def test_container_write_read(self, json_cache):
        values = [[0, 1, 2, 3], (0, 11, 22, 33)]
        for i, val in enumerate(values):
            json_cache.save(val, f"containerVariant{i}")

        for i, expected in enumerate(values):
            # Tuples get returned as lists from JSON
            assert list(json_cache.get(f"containerVariant{i}")) == list(expected)

        json_cache.save(values, "containerVariants")
        with pytest.raises(AssertionError):
            assert values == json_cache.get("containerVariants")
        
if __name__ == "__main__":
    import pytest

    # Runs pytest directly on this file with interactive flags
    # pytest.main([__file__, "-v", "-s"])
    pytest.main([__file__, "-v", "--pdb"])
    
    
    
