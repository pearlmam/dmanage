# -*- coding: utf-8 -*-

class MissingModule:
    """Placeholder for missing optional dependencies."""
    def __init__(self, name):
        self._name = name

    def __getattr__(self, item):
        raise ImportError(
            f"The '{self._name}' package is required to use 'pd.{item}'. "
            f"Please install it using 'pip install {self._name}'."
        )
        
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = MissingModule("pandas")
    HAS_PANDAS = False
    
try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    pl = MissingModule("polars")
    HAS_POLARS = False