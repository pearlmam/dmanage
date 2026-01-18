# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import Pyro5.api

from dmanage.methods import wrapper
from dmanage.unit import make_data_unit
from dmanage.group import make_data_group
from dmanage.decorate import override

N=10000
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

class Component1():
    """To test component"""
    def __init__(self):
        self.attr = 'Component1 attribute'
        self.Comp = Component2()
        
    #@Pyro5.api.expose
    @override()
    def func(self):
        return 'Component1 Func'

class Parent():
    """To test inherited methods"""
    def __init__(self,*args,**kwargs):
        self.parentAttr = 'Parent attribute'
    def parent_func(self):
        return 'Parent Func'

DataUnit = make_data_unit(Parent)
length = 100
class MyDataUnit(DataUnit):
    """Class to share and proxy"""
    def __init__(self,dataPath='path.test'):
        super().__init__(dataPath)
        self.Comp = Component1()  
    
    def is_valid(self):
        return '.test' in self.dataPath
    
    @override()
    def parallel_method(self,arg0,nc=1):
        #print("nc=%d"%nc)
        func = wrapper.parallelize_iterator_method(iteration_method)
        return func(arg0,nc=nc)
    
    @override()
    def gen_DataFrame(self,variant=1):
        """To test DataFrame transfer"""
        if variant == 1:
            data = pd.DataFrame({'A':1.2,'B':"I'm a string",'C':True,'D':[x for x in range(10)]})
        elif variant == 2:
            index = np.linspace(0,100,length)
            values = index*2
            data = pd.DataFrame({'current':values},index=index)
            data.index.name = 'voltage'
        else:
            time = np.linspace(0,100,length)
            x = np.linspace(0,1,length)
            X,T = np.meshgrid(x,time)
            voltage = -X**2+0.5+T
            data = pd.DataFrame(voltage,columns=x,index=time)
            data.columns.name = 'x'
            data.index.name = 'Time'
            data = data.stack()
            data.name = 'voltage'
            data = pd.DataFrame(data)
        return data
    
    #@Pyro5.api.expose
    @override()
    def gen_Series(self):
        """To test Series transfer"""
        time = np.linspace(0,100,length)
        x = np.linspace(0,1,100)
        X,T = np.meshgrid(x,time)
        voltage = -X**2+0.5+T
        data = pd.DataFrame(voltage,columns=x,index=time)
        data.columns.name = 'x'
        data.index.name = 'Time'
        data = data.stack()
        data.name = 'voltage'
        return data
    
    @override()
    def gen_numpy(self,):
        """Numpy should only work with dill and pickle serialization"""
        data = np.linspace(0,10,100)
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
    
    def access_priviate_method(self):
        # should be wrapped
        return self._private_method()