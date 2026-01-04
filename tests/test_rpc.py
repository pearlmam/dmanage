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
import copy

"""   Constants   """
dataPath = '/path/'
host= '127.0.0.1'
user = getpass.getuser()
obj = 'MyDataUnit'
module = file_path = os.path.splitext(os.path.realpath(__file__))[0]

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
    
    def add_component(self):
        self.AddedComp = Component3()

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
        proxyDU = Factory.create(obj,module=module,dataPath=dataPath)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        
        # test get_components
        localDU.add_component()
        proxyDU.add_component()
        proxyDU._register_components()
        
        # check dir() implementation
        proxyAttrs = [attr for attr in dir(proxyDU) if not attr.startswith('_')]
        localAttrs = [attr for attr in dir(localDU) if not attr.startswith('_')]
        # remove unexposed proxy attrs from local
        # localAttrs.remove('dataUnit')
        # localAttrs.remove('parentAttr')
        
        assert proxyAttrs == localAttrs
        
        
        
        # test numpy
        with pytest.raises(TypeError):
            proxyDU.gen_numpy()
        Pyro5.api.config.SERIALIZER = "pickle"
        assert np.array_equal(proxyDU.gen_numpy(),localDU.gen_numpy())
        Pyro5.api.config.SERIALIZER = "serpent"
        with pytest.raises(TypeError):
            proxyDU.gen_numpy()
        
        # close DataUnit Factory Proxy?
        
        # # stop factory
        # self.run = False
        # time.sleep(3)
        #assert thread.is_alive() is False
        
    def test_factory(self):
        """Make sure factor is running with terminal command 'dmanage-factory'"""
        uri = "PYRO:ProxyFactory@localhost:44444"
        Factory = rpc.ProxyFactory(uri=uri)
        
        
        ######   security   #######
        secureLocation = module
        insecureLocation = '/Some/Insecure/Path'
        restrictedLocation = os.path.join(rpc.SECURE_LOCATIONS[0],'Some/Path/In/%s/Directory'%rpc.RESTRICTED_LOCATIONS[0])
        Factory.create(obj,module=secureLocation,dataPath=dataPath)
        with pytest.raises(Exception):
            Factory.create(obj,module=insecureLocation,dataPath=dataPath)
        with pytest.raises(Exception): 
            Factory.create(obj,module=restrictedLocation,dataPath=dataPath)
        
        
        ###### Cant currently set secure locations without hard coding in rpc... Config file?
        # originalSECURE_LOCATIONS = copy.copy(rpc.SECURE_LOCATIONS)
        # nowNotSecureLocation = secureLocation
        # rpc.set_secure_location(['/somewhere/outside/home/directory'])
        # with pytest.raises(Exception): 
        #     Factory.create(obj,module=nowNotSecureLocation,dataPath=dataPath)
        
        # rpc.set_secure_location(['/somewhere/outside/home/directory'])
        # # Should work again
        # rpc.set_secure_location(originalSECURE_LOCATIONS)
        # Factory.create(obj,module=secureLocation,dataPath=dataPath)
        
        
        
if __name__ == "__main__":
    test = TestAllLocal()
    test.test_expose_all()
    test.test_dataUnit_proxy()
    test.test_factory()
    # localDU = MyDataUnit(dataPath)
    # comps = rpc.get_components(localDU)
    # print(comps)
    
    uri = "PYRO:ProxyFactory@localhost:44444"
    Factory = rpc.ProxyFactory(uri=uri)
    proxyDU = Factory.create(obj,module=module,dataPath=dataPath)
    # proxyDU = Factory.create(obj,module='/Some/Insecure/Path',dataPath=dataPath)
    # proxyDU = Factory.create(obj,module='/home***REMOVED***Some/Path/In/anaconda3/Directory',dataPath=dataPath)
    
