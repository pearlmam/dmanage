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

from testObjects import MyDataUnit,MyNewDataUnit
from testObjects import MyDataGroup,MyNewDataGroup
from testObjects import Parent

"""   Constants   """
baseDir = '/path/to/baseDir/'
dataPath = 'path.test'
testN = 100
kwargsDU = {'dataPath':dataPath}
kwargsDG = {'baseDir':baseDir,'unitType':'test','testN':testN}
host= '127.0.0.1'
port = 44444
user = getpass.getuser()
objDU = 'MyDataUnit'
objDG = 'MyDataGroup'
objNDU = 'MyNewDataUnit'
objNDG = 'MyNewDataGroup'
localModule = file_path = os.path.splitext(os.path.realpath(__file__))[0]
remoteModule = '/home/***REMOVED***/Documents/developmentProjects/dmanage/tests/test_rpc'


parallelDUInput = np.linspace(0,100,101).tolist()
#parallelDGInput = [parallelDUInput]*4



module = localModule
# module = remoteModule

class TestAllLocal(TestCase):
    run = True
    def _run(self):
        return self.run
    
    def _start_factory(self):
        loopCondition = lambda : self._run()
        rpc.start_factory(loopCondition=loopCondition)
        
    def test_expose_all(self):
        # nothing is exposed
        DU = MyDataUnit(dataPath)
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
        Pyro5.api.config.SERIALIZER = "serpent"
        localDU = MyDataUnit(dataPath)
        # start Factory
        # # thread = Thread(target=self._start_factory)
        # thread.daemon = True
        # thread.start()
        # time.sleep(3)
        #assert thread.is_alive() is True
        uri = "PYRO:ProxyFactory@localhost:%s"%port
        Factory = rpc.ProxyFactory(uri=uri)
        
        proxyDU = Factory.create(objDU,module=module,kwargs=kwargsDU)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert (proxyDU.parallel_method(parallelDUInput,nc=4) == localDU.parallel_method(parallelDUInput,nc=4))
        
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
        
    def test_dataGroup_proxy(self):
        Pyro5.api.config.SERIALIZER = "serpent"
        localDG = MyDataGroup(baseDir,unitType='test',testN=testN)
        
        uri = "PYRO:ProxyFactory@localhost:%s"%port
        Factory = rpc.ProxyFactory(uri=uri)
        proxyDG = Factory.create(objDG,module=module,kwargs=kwargsDG)
        
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=4), proxyDG.gen_DataFrame(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=1), proxyDG.gen_DataFrame(nc=1))])
        assert all([(local==remote) for local, remote in zip(localDG.Comp.func(nc=1), proxyDG.Comp.func(nc=1))])
        
        ### parallel methods and nc pass through
        assert all([local==remote for local, remote in 
                    zip(proxyDG.parallel_method(parallelDUInput,ncPass=True,nc=4),
                        localDG.parallel_method(parallelDUInput,ncPass=True,nc=4))])
        assert all([local==remote for local, remote in 
                    zip(proxyDG.parallel_method(parallelDUInput,ncPass=False,nc=4),
                        localDG.parallel_method(parallelDUInput,ncPass=False,nc=4))])
        
        ## test get_DataUnit()
        proxyDU = proxyDG.get_DataUnit(0)
        localDU = localDG.get_DataUnit(0)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        Pyro5.api.config.SERIALIZER = "pickle"
        proxyDU = proxyDG.get_DataUnit(0)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        Pyro5.api.config.SERIALIZER = "serpent"
        
    def test_dataUnit_multiple_inheritance(self):
        Pyro5.api.config.SERIALIZER = "serpent"
        localDU = MyNewDataUnit()
        
        uri = "PYRO:ProxyFactory@localhost:%s"%port
        Factory = rpc.ProxyFactory(uri=uri)
        proxyDU = Factory.create(objNDU,module=module,kwargs=kwargsDU)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.process_df().equals(localDU.process_df())
        assert proxyDU.process_series().equals(localDU.process_series())
        assert proxyDU.parallel_method(parallelDUInput,nc=4) == localDU.parallel_method(parallelDUInput,nc=4)

        
        # test get_components
        localDU.add_component()
        proxyDU.add_component()
        proxyDU._register_components()
        
        # check dir() implementation
        proxyAttrs = [attr for attr in dir(proxyDU) if not attr.startswith('_')]
        localAttrs = [attr for attr in dir(localDU) if not attr.startswith('_')]
        assert proxyAttrs == localAttrs
        
        # test numpy
        with pytest.raises(TypeError):
            proxyDU.gen_numpy()
        Pyro5.api.config.SERIALIZER = "pickle"
        assert np.array_equal(proxyDU.gen_numpy(),localDU.gen_numpy())
        Pyro5.api.config.SERIALIZER = "serpent"
        with pytest.raises(TypeError):
            proxyDU.gen_numpy()
        
    def test_dataGroup_multiple_inheritance(self):
        localDG = MyNewDataGroup(baseDir,unitType='test',testN=testN)
        
        uri = "PYRO:ProxyFactory@localhost:%s"%port
        Factory = rpc.ProxyFactory(uri=uri)
        proxyDG = Factory.create(objNDG,module=module,kwargs=kwargsDG)
        
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=4), proxyDG.gen_DataFrame(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=1), proxyDG.gen_DataFrame(nc=1))])
        assert all([(local==remote) for local, remote in zip(localDG.Comp.func(nc=1), proxyDG.Comp.func(nc=1))])
        
        # multiple inheritance
        assert all([all(local==remote) for local, remote in zip(localDG.process_df(nc=4), proxyDG.process_df(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.process_df(nc=1), proxyDG.process_df(nc=1))])
        assert all([all(local==remote) for local, remote in zip(localDG.process_series(nc=4), proxyDG.process_series(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.process_series(nc=1), proxyDG.process_series(nc=1))])
        
        ### parallel methods and nc pass through
        assert all([local==remote for local, remote in 
                    zip(proxyDG.parallel_method(parallelDUInput,ncPass=True,nc=4),
                        localDG.parallel_method(parallelDUInput,ncPass=True,nc=4))])
        assert all([local==remote for local, remote in 
                    zip(proxyDG.parallel_method(parallelDUInput,ncPass=False,nc=4),
                        localDG.parallel_method(parallelDUInput,ncPass=False,nc=4))])
        
        ## test get_DataUnit()
        proxyDU = proxyDG.get_DataUnit(0)
        localDU = localDG.get_DataUnit(0)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        Pyro5.api.config.SERIALIZER = "pickle"
        proxyDU = proxyDG.get_DataUnit(0)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()  
        
        # multiple inheritance
        assert proxyDU.process_df().equals(localDU.process_df())
        assert proxyDU.process_series().equals(localDU.process_series())
        
    def test_factory(self):
        """Make sure factor is running with terminal command 'dmanage-factory'"""
        uri = "PYRO:ProxyFactory@localhost:44444"
        Factory = rpc.ProxyFactory(uri=uri)
        
        
        ######   security   #######
        secureLocation = module
        insecureLocation = '/Some/Insecure/Path'
        restrictedLocation = os.path.join(rpc.SECURE_LOCATIONS[0],'Some/Path/In/%s/Directory'%rpc.RESTRICTED_LOCATIONS[0])
        Factory.create(objDU,module=secureLocation,kwargs=kwargsDU)
        with pytest.raises(Exception):
            Factory.create(objDU,module=insecureLocation,kwargs=kwargsDU)
        with pytest.raises(Exception): 
            Factory.create(objDU,module=restrictedLocation,kwargs=kwargsDU)
        
        
        ###### Cant currently set secure locations without hard coding in rpc... Config file?
        # originalSECURE_LOCATIONS = copy.copy(rpc.SECURE_LOCATIONS)
        # nowNotSecureLocation = secureLocation
        # rpc.set_secure_location(['/somewhere/outside/home/directory'])
        # with pytest.raises(Exception): 
        #     Factory.create(objDU,module=nowNotSecureLocation,kwargs=kwargsDU)
        
        # rpc.set_secure_location(['/somewhere/outside/home/directory'])
        # # Should work again
        # rpc.set_secure_location(originalSECURE_LOCATIONS)
        # Factory.create(objDU,module=secureLocation,kwargs=kwargsDU)
        
        
        
if __name__ == "__main__":
    test = TestAllLocal()
    test.test_expose_all()
    test.test_dataUnit_proxy()
    test.test_dataGroup_proxy()
    test.test_dataUnit_multiple_inheritance()
    test.test_dataGroup_multiple_inheritance()
    test.test_factory()
    
    #localDU = MyDataUnit(dataPath)
    
    # # comps = rpc.get_components(localDU)
    # # print(comps)
    # uri = "PYRO:ProxyFactory@localhost:%s"%port
    # Factory = rpc.ProxyFactory(uri=uri)
    # proxyDU = Factory.create(objDU,module=module,kwargs=kwargsDU)
    
    # Pyro5.api.config.SERIALIZER = "pickle"
    
    # localDG = MyDataGroup(baseDir,unitType='test')
    # uri = "PYRO:ProxyFactory@localhost:44444"
    # Factory = rpc.ProxyFactory(uri=uri)
    
    # proxyDG = Factory.create(objDG,module=module,kwargs=kwargsDG)
    
    # proxyDU = proxyDG.get_DataUnit(0)
    # DF = proxyDG.gen_DataFrame()
    

    
