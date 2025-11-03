# -*- coding: utf-8 -*-
import time
from dmanage import dfmethods as dfm
from dmanage.dataDir import makeDataDir
from dmanage.dfmethods.plot import Plot
from dmanage.loaders.vsim import vsim

DFP = Plot(backEnd = 'qtagg')


folder = './test_data/vsim_data/VDC-87.8e3/'
DataDir = makeDataDir(vsim.VSim)
DD = DataDir(folder)


# Testing convert
histName = 'Pout'
df0 = DD.Hists.readAsDF(histName)
df1 = dfm.signal.applyFilter(df0, method='low', cutoff=100e6)

fignum = 1
fig,ax = DFP.plot1D(df0,fig=fignum)
fig,ax = DFP.plot1D(df1,fig=fignum,clear=False)

partName = 'electronsT'
df0 = DD.Parts.readAsDF(steps='all',partType=partName,nc=4)
#mem_usage = memory_usage(dfm.convert.cart2Cyl(df0,xyCols=['x','y'],uxyCols = ['ux','uy'],rphiCols=['r','phi'],phiRange='2pi',inplace=False,nc=1))
startTime = time.time()
df1 = dfm.convert.cart2Cyl(df0,xyCols=['x','y'],uxyCols = ['ux','uy'],rphiCols=['r','phi'],phiRange='2pi',nc=1)
exectutionTime = time.time() - startTime
print('dfm.convert.cart2Cyl() took %0.3f seconds'%exectutionTime)

print(df0.columns)
print(df1.columns)
