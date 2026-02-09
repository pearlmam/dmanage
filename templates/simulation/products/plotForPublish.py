# -*- coding: utf-8 -*-

import sys
sys.path.append('../core/')
from dataGroup import MyDataGroup

dataPath = 'path/to/data/used/for/final/report'

DG = MyDataGroup(dataPath)

"""
Make a whole bunch of pretty plots of the data that are used for publication
This is similar to the analysis folder, but differs in that scripts living here
should remain untouched once finilized. I use these for final analyisis scripts
on finilized data.
"""