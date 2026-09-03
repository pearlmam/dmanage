# -*- coding: utf-8 -*-
import dmanage
import dmanage.remote.rpc as rpc
import Pyro5.api
import time
import numpy as np
import pytest
from unittest import TestCase
import getpass

from helpers.strata_objects import Parent,MyDataGroup,MyDataUnit,MyNewDataGroup,MyNewDataUnit
 

nc_pass_test = True 
dmanage.config.PARALLEL_BACKEND="multiprocessing"
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

# parallelDUInput = np.linspace(0,100,101).tolist()
parallelDUInput = np.linspace(0,100,101).tolist()
#parallelDGInput = [parallelDUInput]*4

Pyro5.api.config.PICKLE_ENABLE=False

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
        
        proxyDU = Factory.create(objDU,**kwargsDU)
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert (proxyDU.parallel_method(parallelDUInput,nc=4) == localDU.parallel_method(parallelDUInput,nc=4))
        
        #### test attribute proxy access
        proxyDU = Factory.MyDataUnit(**kwargsDU)
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
        
        if Pyro5.api.config.PICKLE_ENABLE:
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
        proxyDG = Factory.create(objDG,**kwargsDG)
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=4), proxyDG.gen_DataFrame(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=1), proxyDG.gen_DataFrame(nc=1))])
        assert all([(local==remote) for local, remote in zip(localDG.Comp.func_override(nc=1), proxyDG.Comp.func_override(nc=1))])
        
        ### parallel arrays and nc pass through
        if nc_pass_test:
            assert all([local==remote for local, remote in 
                    zip(proxyDG.parallel_method(parallelDUInput,ncPass=True,nc=4),
                        localDG.parallel_method(parallelDUInput,ncPass=True,nc=4))])
        assert all([local==remote for local, remote in 
                    zip(proxyDG.parallel_method(parallelDUInput,ncPass=False,nc=4),
                        localDG.parallel_method(parallelDUInput,ncPass=False,nc=4))])
        
        # this tests access to private DataUnit methods from the DataGroup with multiprocessing
        assert (localDG.access_private_method(nc=4) == proxyDG.access_private_method(nc=4))
        
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
        
        if Pyro5.api.config.PICKLE_ENABLE:
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
        proxyDU = Factory.create(objNDU,**kwargsDU)
        assert proxyDU.process_df().equals(localDU.process_df())
        assert proxyDU.process_series().equals(localDU.process_series())

    def test_dataGroup_multiple_inheritance(self):
        localDG = MyNewDataGroup(baseDir,unitType='test',testN=testN)
        
        uri = "PYRO:ProxyFactory@localhost:%s"%port
        Factory = rpc.ProxyFactory(uri=uri)
        proxyDG = Factory.create(objNDG,**kwargsDG)
        
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=4), proxyDG.gen_DataFrame(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.gen_DataFrame(nc=1), proxyDG.gen_DataFrame(nc=1))])
        assert all([(local==remote) for local, remote in zip(localDG.Comp.func_override(nc=1), proxyDG.Comp.func_override(nc=1))])
        
        # multiple inheritance
        assert all([all(local==remote) for local, remote in zip(localDG.process_df(nc=4), proxyDG.process_df(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.process_df(nc=1), proxyDG.process_df(nc=1))])
        assert all([all(local==remote) for local, remote in zip(localDG.process_series(nc=4), proxyDG.process_series(nc=4))])
        assert all([all(local==remote) for local, remote in zip(localDG.process_series(nc=1), proxyDG.process_series(nc=1))])
        
        ### parallel arrays and nc pass through
        if nc_pass_test:
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
        
        # multiple inheritance
        assert proxyDU.process_df().equals(localDU.process_df())
        assert proxyDU.process_series().equals(localDU.process_series())
        
        if Pyro5.api.config.PICKLE_ENABLE:
            Pyro5.api.config.SERIALIZER = "pickle"
            proxyDU = proxyDG.get_DataUnit(0)
            assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
            assert proxyDU.gen_DataFrame().equals(localDU.gen_DataFrame())
            
            # multiple inheritance
            assert proxyDU.process_df().equals(localDU.process_df())
            assert proxyDU.process_series().equals(localDU.process_series())
            Pyro5.api.config.SERIALIZER = "serpent"
        
    def test_factory(self):
        """Make sure factor is running with terminal command 'dmanage-factory'"""
        uri = "PYRO:ProxyFactory@localhost:44444"
        Factory = rpc.ProxyFactory(uri=uri)
        
        
        ######   security   #######

        insecureObj = 'os'  # loading this module
        with pytest.raises(Exception):
            Factory.create(insecureObj,**kwargsDU)

        ###### Cant currently set secure locations without hard coding in rpc... Config file?
        # originalSECURE_LOCATIONS = copy.copy(rpc.SECURE_LOCATIONS)
        # nowNotSecureLocation = secureLocation
        # rpc.set_secure_location(['/somewhere/outside/home/directory'])
        # with pytest.raises(Exception): 
        #     Factory.create(objDU,module=nowNotSecureLocation,**kwargsDU)
        
        # rpc.set_secure_location(['/somewhere/outside/home/directory'])
        # # Should work again
        # rpc.set_secure_location(originalSECURE_LOCATIONS)
        # Factory.create(objDU,module=secureLocation,**kwargsDU)
        
        
if __name__ == "__main__":
    t0 = time.perf_counter()
    test = TestAllLocal()
    test.test_expose_all()
    test.test_dataUnit_proxy()
    test.test_dataGroup_proxy()
    test.test_dataUnit_multiple_inheritance()
    test.test_dataGroup_multiple_inheritance()
    test.test_factory()
    print(f"\nFinished in {time.perf_counter() - t0:0.2f} seconds")
    
    #localDU = MyDataUnit(dataPath)
    
    # # comps = rpc.get_components(localDU)
    # # print(comps)
    # uri = "PYRO:ProxyFactory@localhost:%s"%port
    # Factory = rpc.ProxyFactory(uri=uri)
    
    # proxyDU = Factory.create(objDU,**kwargsDU)
    # kwargsDU = {'dataPath':'path2.test'}
    # proxyDU2 = Factory.create(objDU,proxy_reload=True,**kwargsDU)
    
    
    # Pyro5.api.config.SERIALIZER = "pickle"
    
    # localDG = MyDataGroup(baseDir,unitType='test')
    # uri = "PYRO:ProxyFactory@localhost:44444"
    # Factory = rpc.ProxyFactory(uri=uri)
    
    # proxyDG = Factory.create(objDG,**kwargsDG)
    # a = localDG.parallel_method(parallelDUInput,ncPass=True,nc=4)
    # b = proxyDG.parallel_method(parallelDUInput,ncPass=True,nc=4)
    
    # proxyDU = proxyDG.get_DataUnit(0)
    # DF = proxyDG.gen_DataFrame()
    
    