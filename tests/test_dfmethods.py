# -*- coding: utf-8 -*-
import time
from dmanage import dfmethods as dfm
from dmanage.unit import make_data_unit
from dmanage.dfmethods import plot
from dmanage.plugins.vsim.loader import VSim


folder = './test_data/vsim_data/VDC-87.8e3/'
DataDir = make_data_unit(VSim)
DD = DataDir(folder)


# Testing convert
histName = 'Pout'
df0 = DD.Hists.read_as_df(histName)
df1 = dfm.signal.apply_filter(df0, method='low', cutoff=100e6)

fignum = 1
fig,ax = plot.plot1d(df0, fig=fignum)
fig,ax = plot.plot1d(df1, fig=fignum, clear=False)

partName = 'electronsT'
df0 = DD.Parts.read_as_df(steps='all', partType=partName, nc=4)
#mem_usage = memory_usage(dfm.convert.cart2Cyl(df0,xyCols=['x','y'],uxyCols = ['ux','uy'],rphiCols=['r','phi'],phiRange='2pi',inplace=False,nc=1))
startTime = time.time()
df1 = dfm.convert.cart_to_cyl(df0, xyCols=['x', 'y'], uxyCols = ['ux', 'uy'], rphiCols=['r', 'phi'], phiRange='2pi', nc=1)
exectutionTime = time.time() - startTime
print('dfm.convert.cart2Cyl() took %0.3f seconds'%exectutionTime)

print(df0.columns)
print(df1.columns)
