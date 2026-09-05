# -*- coding: utf-8 -*-

import dmanage.viz as viz
from dmanage._compat import pd
import time
import hvplot.pandas
import panel as pn


## get data

from helpers.viz_data import df

def check_threads():
    import threading
    for i,t in enumerate(threading.enumerate()):
        print(f"thread {i}:{t}, has stop: {hasattr(t, "stop")}")


# check_threads()
# explorer = viz.launch_explorer(df)
# check_threads()

explorer = viz.HvPlotExplorer(df)
explorer.start()

# pn.extension()
# df = viz.sanitize_df(df)
# explorer = df.hvplot.explorer()
# thread = pn.serve(
#     explorer,
#     port=5006,
#     address="127.0.0.1",
#     threaded=True,
#     show=True,
#     websocket_origin="*"
#     )
