# -*- coding: utf-8 -*-
from dmanage._compat import pd
from .client import ProxyWrap

try:
    import Pyro5.api
    import Pyro5.serializers
    HAS_PICKLE = hasattr(Pyro5.api.config, "PICKLE_ENABLE")
except ImportError:
    HAS_PICKLE = False

# --- URI Hooks ---
URIHook = type("URIHook", (str,), {})


def uri_to_dict(uri):
    return {"__class__": "URIDict", "uri": str(uri)}


def dict_to_uri(classname, d):
    return ProxyWrap(str(d["uri"]))


Pyro5.api.register_class_to_dict(URIHook, uri_to_dict)
Pyro5.api.register_dict_to_class("URIDict", dict_to_uri)

if HAS_PICKLE:
    def uri_to_proxy(uri):
        return ProxyWrap(str(uri))

    Pyro5.api.register_pickle_loads_hook("URIHook", uri_to_proxy)

# --- Pandas Hooks ---
orient = "tight"


def df_to_dict(df):
    return {"__class__": "DataFrameDict", "DataFrame": df.to_dict(orient=orient)}


def dict_to_df(classname, d):
    serializer = Pyro5.serializers.serializers[Pyro5.api.config.SERIALIZER]
    data = serializer.recreate_classes(d["DataFrame"])
    return pd.DataFrame.from_dict(data, orient=orient)


def series_to_dict(series):
    return {"__class__": "SeriesDict", "Series": series.to_frame().to_dict(orient=orient)}


def dict_to_series(classname, d):
    serializer = Pyro5.serializers.serializers[Pyro5.api.config.SERIALIZER]
    data = serializer.recreate_classes(d["Series"])
    return pd.DataFrame.from_dict(d["Series"], orient=orient).iloc[:, 0]


Pyro5.api.config.SERIALIZER = "serpent"
Pyro5.api.register_class_to_dict(pd.core.frame.DataFrame, df_to_dict)
Pyro5.api.register_dict_to_class("DataFrameDict", dict_to_df)
Pyro5.api.register_class_to_dict(pd.core.frame.Series, series_to_dict)
Pyro5.api.register_dict_to_class("SeriesDict", dict_to_series)