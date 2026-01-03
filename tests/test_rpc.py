# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import dmanage.remote.rpc as rpc
import Pyro5.api

import pytest
from unittest import TestCase
import getpass
import os

"""   Constants   """
dataPath = '/path/'
host= '127.0.0.1'
user = getpass.getuser()
obj = 'MyDataUnit'
module = file_path = os.path.splitext(os.path.realpath(__file__))[0]

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
    def func(self):
        return 'Component1 Func'

class Parent():
    """To test inherited methods"""
    def __init__(self):
        self.parentAttr = 'Parent attribute'
    def parent_func(self):
        return 'Parent Func'

length = 100
class MyDataUnit(Parent):
    """Class to share and proxy"""
    def __init__(self,dataPath='path'):
        self.dataUnit = dataPath
        self.Comp = Component1()  
        super().__init__()
        
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
    
    def gen_numpy(self,):
        """Numpy should only work with dill and pickle serialization"""
        data = np.linspace(0,10,100)
        # data = {'A':data}
        return data

class TestAllLocal(TestCase):
    run = True
    def _run(self):
        return self.run
    
    def _start_factory(self):
        loopCondition = lambda : self._run()
        rpc.start_factory(loopCondition=loopCondition)
        
    def test_expose_all(self):
        # nothing is exposed
        DU = MyDataUnit('path')
        assert getattr(DU,'_pyroExposed',False) is False
        assert getattr(DU.parent_func,'_pyroExposed',False) is False
        assert getattr(MyDataUnit,'_pyroExposed',False) is False
        assert getattr(Parent,'_pyroExposed',False) is False
        
        rpc.expose_all(DU)
        
        # class and instance are now exposed
        assert getattr(MyDataUnit,'_pyroExposed',False) is True
        assert getattr(Parent,'_pyroExposed',False) is True
        assert getattr(DU,'_pyroExposed',False) is True
        assert getattr(DU.parent_func,'_pyroExposed',False) is True
    
        # component is not exposed
        assert getattr(DU.Comp,'_pyroExposed',False) is False
        rpc.expose_all(DU.Comp)
        assert getattr(DU.Comp,'_pyroExposed',False) is True
        
    
    def test_dataUnit_proxy(self):
        """Make sure factor is running with terminal command 'dmanage-factory'"""
        localDU = MyDataUnit(dataPath)
        # start Factory
        # # thread = Thread(target=self._start_factory)
        # thread.daemon = True
        # thread.start()
        # time.sleep(3)
        #assert thread.is_alive() is True
        uri = "PYRO:ProxyFactory@localhost:44444"
        Factory = rpc.ProxyFactory(uri=uri)
        proxyDU = Factory.create(obj,module=module,name='DataDir',dataPath=dataPath)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        
        # test numpy
        with pytest.raises(TypeError):
            proxyDU.gen_numpy()
        Pyro5.api.config.SERIALIZER = "pickle"
        assert np.array_equal(proxyDU.gen_numpy(),localDU.gen_numpy())
        Pyro5.api.config.SERIALIZER = "serpent"
        # # stop factory
        # self.run = False
        # time.sleep(3)
        #assert thread.is_alive() is False
        
if __name__ == "__main__":
    test = TestAllLocal()
    test.test_expose_all()
    test.test_dataUnit_proxy()

