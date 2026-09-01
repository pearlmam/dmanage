
''' Example configuration file for dmanage.remote.rpc features'''

import Pyro5
from tests.helpers.strata_objects import Parent,MyDataGroup,MyDataUnit,MyNewDataGroup,MyNewDataUnit

ONLY_EXPOSED = False
Pyro5.api.config.PICKLE_ENABLE = True  # Enabling pickle is a massive security risk

EXPOSED_OBJECTS = {
    "Parent":Parent,
    "MyDataGroup":MyDataGroup,
    "MyDataUnit":MyDataUnit,
    "MyNewDataGroup":MyNewDataGroup,
    "MyNewDataUnit":MyNewDataUnit,
    }

