
''' Example configuration file for dmanage.remote.rpc features'''

import Pyro5
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from strata_objects import Parent,MyDataGroup,MyDataUnit,MyNewDataGroup,MyNewDataUnit

ONLY_EXPOSED = False
Pyro5.api.config.PICKLE_ENABLE = False # Enabling pickle is a massive security risk

EXPOSED_OBJECTS = {
    "Parent":Parent,
    "MyDataGroup":MyDataGroup,
    "MyDataUnit":MyDataUnit,
    "MyNewDataGroup":MyNewDataGroup,
    "MyNewDataUnit":MyNewDataUnit,
    }
