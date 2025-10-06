# -*- coding: utf-8 -*-

from dmanage.dataDir import DataDir

folder = './test_data/vsim_data/'
DD = DataDir(folder)

##############################################################
## checking the structure of the class
##############################################################

print('Checking types: Histories:\n')
print(DD.Hists.types)

print('\nChecking types: Particles:\n')
print(DD.Parts.types)

print('\nChecking types: Fields:\n')
print(DD.Fields.types)

print('\nChecking types: Geometries:\n')
print(DD.Geos.files)

##############################################################
## check data loading
##############################################################
print('\nRead 1D History')
histName = 'Pout'
df = DD.Hists.readAsDF(histName)
print(df)

print('\nRead 2D Vector History')
histName = 'EedgeCircleR200'
df = DD.Hists.readAsDF(histName)
print(df)

print('\nRead All particles')
partName = 'electrons'
df = DD.Parts.readAllAsDF(partName,nc=4)
print(df)

print('\nRead All Fields')
fieldName = 'E'
df = DD.Fields.readAllAsDF(fieldName,nc=4)
print(df)

##############################################################
## input deck reading
##############################################################
print('\nRead Pre Variables')
varNames = ['VDC', 'BSTATIC','PRF_AVG','undefinedVariable']
out = DD.PreVars.read(varNames,warn=True)
print(out)





