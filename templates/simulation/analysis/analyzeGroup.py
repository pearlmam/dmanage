# -*- coding: utf-8 -*-
"""
This analysis folder is where to put specific analysis scripts. The core should
perform base functionality and is more stagnant. This is less stangant and could 
be modified for every use. The analysis may be finilized, but the inputs might
change often to analyse different data sets. For finilized analysis scripts 
that dont change very often, consider puting them in products.
"""


import sys
sys.path.append('../core/')
from dataGroup import MyDataGroup

dataPath = 'path/to/data'

DG = MyDataGroup(dataPath)

# do operations