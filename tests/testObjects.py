# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import Pyro5.api
# from matplotlib import pyplot as plt
import os

from dmanage.ops.dfmethods import plot
from dmanage.parallel import parallelize_iterator_method
from dmanage.strata import make_data_unit, make_data_group, override, plot_override, helpers
from dmanage.metadata import metastring

def iteration_method(arg0):
    a = np.linspace(0,100,101)*arg0
    return a.mean().tolist()

class Component3:
    def func(self):
        return 'Component3 Func'

class Component2():
    """To test component of component"""
    def __init__(self):
        self.attr = 'Component2 attribute'
    
    def func(self):
        return 'Component2 Func'
    
    # @Pyro5.api.expose
    @override()
    def func_override(self):
        return 'Component2 Func overriden'

class Component1():
    """To test component"""
    def __init__(self):
        self.attr = 'Component1 attribute'
        self.Comp = Component2()
    
    def func(self):
        return 'Component1 Func'
    
    # @Pyro5.api.expose
    @override()
    def func_override(self):
        return 'Component1 Func overriden'
    
    @override()
    def parallel_method(self,arg0,nc=1):
        #print("nc=%d"%nc)
        func = parallelize_iterator_method(iteration_method)
        return func(arg0,nc=nc)

class Parent():
    """To test inherited arrays"""
    def __init__(self,*args,**kwargs):
        self.parentAttr = 'Parent attribute'
    
    def parent_func(self):
        return 'Parent Func'
    
    @override()
    def parent_func_override(self):
        return 'Parent Func overriden'

DataUnit = make_data_unit(Parent)
class MyDataUnit(DataUnit):
    """Class to share and proxy"""
    def __init__(self,dataPath='file-00.test'):
        super().__init__(dataPath)
        self.Comp = Component1() 
        self.resDir = './data/'
    
    def is_valid(self):
        return '.test' in self.dataPath
    
    @override()
    def parallel_method(self,arg0,nc=1):
        #print("nc=%d"%nc)
        func = parallelize_iterator_method(iteration_method)
        return func(arg0,nc=nc)
    
    @override('plot')
    def plot(self,saveloc=None,fig=1):
        if saveloc is None:
            saveloc = './data/'
        DF = self.gen_DataFrame(variant=1,size=100)
        fig,ax = plot.plot1d(DF,fig=fig)
        savename = 'testplot'
        savetag = self.gen_tag()
        os.makedirs(saveloc,exist_ok=True)
        fig.savefig('%s%s_%s.png'%(saveloc,savename,savetag))
        return fig,ax
    
    @override('savePlot')  # this enables helper.save_plot use with groups
    def plot2(self,fig=1,*args,**kwargs):
        DF = self.gen_DataFrame(variant=1,size=100)
        fig,ax = plot.plot1d(DF,fig=fig)
        helpers.savePlot(self,fig, args,kwargs)
        return fig,ax
    
    @plot_override   # doesnt work well with dataGroups, it looses the looperize wrap...
    def plot3(self,fig=1,*args,**kwargs):
        DF = self.gen_DataFrame(variant=1,size=100)
        fig,ax = plot.plot1d(DF,fig=fig)
        return fig,ax
    
    def gen_tag(self,tagVars='file',format=None):
        tag = '%03i'%metastring.parse(self.dataUnit,checkVars=tagVars)[tagVars][0]
        return tag
    
    @override()     
    def gen_DataFrame(self,variant=0,size=10):
        """To test DataFrame transfer"""
        if variant == 0:
            data = pd.DataFrame({'A':1.2,'B':["I'm a string '%d'"%x for x in range(size)],'C':True,'D':[x for x in range(size)]})
        elif variant == 1:
            index = np.linspace(0,100,size)
            values = index*2
            data = pd.DataFrame({'current':values},index=index)
            data.index.name = 'voltage'
        else: # variant == 2:
            # MultiIndex DataFrame
            time = np.linspace(0,100,size)
            x = np.linspace(0,1,size)
            X,T = np.meshgrid(x,time)
            voltage = -X**2+0.5+T
            data = pd.DataFrame(voltage,columns=x,index=time)
            data.columns.name = 'x'
            data.index.name = 'Time'
            data = data.stack()
            data.name = 'voltage'
            data = pd.DataFrame(data)
        return data
    
    @override()
    def gen_Series(self,variant=0,size=10):
        if variant == 0:
            data = pd.Series(np.linspace(0,10,size).tolist(),name='data')
            
        elif variant == 1:
            """To test Series transfer"""
            time = np.linspace(0,100,size)
            x = np.linspace(0,1,size)
            X,T = np.meshgrid(x,time)
            voltage = -X**2+0.5+T
            data = pd.DataFrame(voltage,columns=x,index=time)
            data.columns.name = 'x'
            data.index.name = 'Time'
            data = data.stack()
            data.name = 'voltage'
        else: # variant == 2:
            data = pd.Series(np.linspace(0,10,size).tolist())
            
        #data = pd.DataFrame(data)
        #print(data)
        return data
    
    @override()
    def gen_numpy(self,size=10):
        """Numpy should only work with dill and pickle serialization"""
        data = np.linspace(0,10,size)
        # data = {'A':data}
        return data
    
    @override()
    def _private_method(self):
        return 'Private Method'
    
    def add_component(self):
        self.AddedComp = Component3()

DataGroup = make_data_group(MyDataUnit)

class MyDataGroup(DataGroup):
    def __init__(self,baseDir,unitType='test',**kwargs):
        super().__init__(baseDir,unitType='test',**kwargs)
    
    def access_private_method(self,nc=1):
        # should be wrapped
        return self._private_method(nc=nc)
    
    # NO override here to process sweep data
    def process_df_sweep(self):
        dfList = self.gen_DataFrame()
        # do something with all the data
        return True
    
class UnitSection1(MyDataUnit):
    @override()
    def process_df(self):
        df = self.gen_DataFrame(1)
        newIndex = ['row %d'%i for i in range(0,len(df))]
        df.index = newIndex
        return df
    
class UnitSection2(MyDataUnit):
    @override()
    def process_series(self):
        series = self.gen_Series(1)
        newIndex = ['row %d'%i for i in range(0,len(series))]
        series.index = newIndex
        return series  
    
class MyNewDataUnit(UnitSection1,UnitSection2):
    pass

NewDataGroup = make_data_group(MyNewDataUnit)
class MyNewDataGroup(NewDataGroup):
    def __init__(self,baseDir,unitType='test',**kwargs):
        super().__init__(baseDir,unitType='test',**kwargs)




if __name__ == "__main__":
    DU1 = UnitSection1()
    DU2 = UnitSection2()
    df = DU1.process_df()
    series = DU2.process_series()
    NDU = MyNewDataUnit()
    
    parallelDUInput = np.linspace(0,100,101)
    NDU.parallel_method(parallelDUInput,nc=4)
    
    NDG = MyNewDataGroup('/base/dir',testN=100)
    
    NDG.parallel_method(range(0,10),ncPass=True,nc=4)
    # print(NDG.process_series(nc=1))
    
    
    
    