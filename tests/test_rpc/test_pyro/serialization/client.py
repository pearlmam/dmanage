#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 24 17:41:22 2025

@author: marcus
"""

import Pyro5.api
import pandas as pd
import dill

# register the special serialization hooks
orient='tight'
def df_to_dict(df):
    print("DataFrame to dict")
    data = df.to_dict(orient=orient)
    data = {'__class__':'DataFrameDict','DataFrame':data}
    return data

def dict_to_df(classname, d):
    print("dict to Dataframe")
    data = pd.DataFrame.from_dict(d['DataFrame'],orient=orient)
    return data

def series_to_dict(series):
    print("Series to dict")
    print(series)

    data = series.to_frame().to_dict(orient=orient)
    data = {'__class__':'SeriesDict','Series':data}
    return data

def dict_to_series(classname, d):
    print("dict to Series")
    data = pd.DataFrame.from_dict(d['Series'],orient=orient).iloc[:,0]
    return data


Pyro5.api.register_class_to_dict(pd.core.frame.DataFrame, df_to_dict)
Pyro5.api.register_dict_to_class("DataFrameDict", dict_to_df)
Pyro5.api.register_class_to_dict(pd.core.frame.Series, series_to_dict)
Pyro5.api.register_dict_to_class("SeriesDict", dict_to_series)


Pyro5.api.config.SERIALIZER = 'serpent'
MyDataDir = Pyro5.api.Proxy("PYRONAME:Obj")
print(MyDataDir.gen_DataFrame(variant=2))
# print(MyDataDir.gen_Series(variant=1))
#MyDataDir.gen_dict()
#MyDataDir.gen_numpy()