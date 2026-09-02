
''' Example configuration file for dmanage.remote.rpc features'''

import Pyro5
import dmanage.config
# import the objects you which to proxy here
from math import sqrt,cos,sin

# Set the configureation options here
ONLY_EXPOSED = False
Pyro5.api.config.PICKLE_ENABLE = False # Enabling pickle is a massive security risk, but can serialize anything
Pyro5.api.config.SERIALIZER = "serpent"# serpent,json?,pickle,dill
dmanage.config.PARALLEL_BACKEND="multiprocessing" # 'multiprocessing' or 'multiprocess'

# add objects here, generally name the key the same as the object
EXPOSED_OBJECTS = {
    "sqrt":sqrt,
    "cos":cos,
    "sin":sin,
    }
