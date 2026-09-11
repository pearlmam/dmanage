# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import Pyro5.api
import pytest
import os
import dmanage
import dmanage.rstrata as rstrata
from helpers.strata_objects import (
    MyDataGroup,
    MyDataUnit,
    MyNewDataGroup,
    MyNewDataUnit,
    Parent,
)

nc_pass_test = True
dmanage.config.PARALLEL_BACKEND = "multiprocessing"

"""    Constants    """
baseDir = "/path/to/baseDir/"
dataPath = "path.test"
testN = 100
kwargsDU = {"dataPath": dataPath}
kwargsDG = {"baseDir": baseDir, "testN": testN}
host = "127.0.0.1"
port = 44444
objDU = "MyDataUnit"
objDG = "MyDataGroup"
objNDU = "MyNewDataUnit"
objNDG = "MyNewDataGroup"

parallelDUInput = np.linspace(0, 100, 101).tolist()
Pyro5.api.config.PICKLE_ENABLE = False
MAX_NC = min(4, os.cpu_count() or 1)

requires_rpc_server = pytest.mark.requires_rpc_server

@pytest.mark.usefixtures("rpc_factory_daemon")
class TestAllLocal:
    def test_expose_all(self):
        # nothing is exposed
        DU = MyDataUnit(dataPath)
        assert getattr(DU, "_pyroExposed", False) is False
        assert getattr(DU.parent_func, "_pyroExposed", False) is False
        assert getattr(MyDataUnit, "_pyroExposed", False) is False
        assert getattr(Parent, "_pyroExposed", False) is False

        rstrata._utils.expose_all(DU)

        # class and instance are now exposed
        assert getattr(MyDataUnit, "_pyroExposed", False) is True
        assert getattr(Parent, "_pyroExposed", False) is True
        assert getattr(DU, "_pyroExposed", False) is True
        assert getattr(DU.parent_func, "_pyroExposed", False) is True

        # component is not exposed
        assert getattr(DU.Comp, "_pyroExposed", False) is False
        rstrata._utils.expose_all(DU.Comp)
        assert getattr(DU.Comp, "_pyroExposed", False) is True

    @requires_rpc_server
    def test_dataUnit_proxy(self):
        """Make sure factory is running with terminal command 'dmanage-factory'"""
        Pyro5.api.config.SERIALIZER = "serpent"
        localDU = MyDataUnit(dataPath)
        uri = f"PYRO:ProxyFactory@{host}:{port}"
        Factory = rstrata.ProxyFactory(uri=uri)

        proxyDU = Factory.create(objDU, **kwargsDU)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.parallel_method(parallelDUInput, nc=MAX_NC) == localDU.parallel_method(parallelDUInput, nc=MAX_NC)

        #### test attribute-like proxy access
        proxyDU = Factory.MyDataUnit(**kwargsDU)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.parallel_method(parallelDUInput, nc=MAX_NC) == localDU.parallel_method(parallelDUInput, nc=MAX_NC)

        # test get_components
        localDU.add_component()
        proxyDU.add_component()
        proxyDU._register_components()

        # check dir() implementation
        proxyAttrs = [attr for attr in dir(proxyDU) if not attr.startswith("_")]
        localAttrs = [attr for attr in dir(localDU) if not attr.startswith("_")]
        assert proxyAttrs == localAttrs

        # test numpy
        with pytest.raises(TypeError):
            proxyDU.gen_numpy()

        if Pyro5.api.config.PICKLE_ENABLE:
            Pyro5.api.config.SERIALIZER = "pickle"
            assert np.array_equal(proxyDU.gen_numpy(), localDU.gen_numpy())

        Pyro5.api.config.SERIALIZER = "serpent"
        with pytest.raises(TypeError):
            proxyDU.gen_numpy()

    @requires_rpc_server
    def test_dataGroup_proxy(self):
        Pyro5.api.config.SERIALIZER = "serpent"
        localDG = MyDataGroup(baseDir, testN=testN)

        uri = f"PYRO:ProxyFactory@{host}:{port}"
        Factory = rstrata.ProxyFactory(uri=uri)
        proxyDG = Factory.create(objDG, **kwargsDG)

        for local_df, remote_df in zip(localDG.gen_DataFrame(nc=MAX_NC), proxyDG.gen_DataFrame(nc=MAX_NC)):
            assert_frame_equal(local_df, remote_df, check_names=False, check_dtype=False)

        for local_df, remote_df in zip(localDG.gen_DataFrame(nc=1), proxyDG.gen_DataFrame(nc=1)):
            assert_frame_equal(local_df, remote_df, check_names=False, check_dtype=False)

        assert all([local == remote for local, remote in zip(localDG.Comp.func_override(nc=1), proxyDG.Comp.func_override(nc=1))])

        ### parallel arrays and nc pass through
        if nc_pass_test:
            assert all([
                local == remote for local, remote in zip(
                    proxyDG.parallel_method(parallelDUInput, ncPass=True, nc=MAX_NC),
                    localDG.parallel_method(parallelDUInput, ncPass=True, nc=MAX_NC)
                )
            ])
        assert all([
            local == remote for local, remote in zip(
                proxyDG.parallel_method(parallelDUInput, ncPass=False, nc=MAX_NC),
                localDG.parallel_method(parallelDUInput, ncPass=False, nc=MAX_NC)
            )
        ])

        # this tests access to private DataUnit methods from the DataGroup with multiprocessing
        assert localDG.access_private_method(nc=MAX_NC) == proxyDG.access_private_method(nc=MAX_NC)

        ## test get_DataUnit()
        proxyDU = proxyDG.get_DataUnit(0)
        localDU = localDG.get_DataUnit(0)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.Comp.func() == localDU.Comp.func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.parent_func() == localDU.parent_func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
        assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()

        if Pyro5.api.config.PICKLE_ENABLE:
            Pyro5.api.config.SERIALIZER = "pickle"
            proxyDU = proxyDG.get_DataUnit(0)
            assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
            assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
            assert proxyDU.Comp.func() == localDU.Comp.func()
            assert proxyDU.Comp.func() == localDU.Comp.func()
            assert proxyDU.parent_func() == localDU.parent_func()
            assert proxyDU.parent_func() == localDU.parent_func()
            assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
            assert proxyDU.Comp.Comp.func() == localDU.Comp.Comp.func()
            Pyro5.api.config.SERIALIZER = "serpent"

    @requires_rpc_server
    def test_dataUnit_multiple_inheritance(self):
        Pyro5.api.config.SERIALIZER = "serpent"
        localDU = MyNewDataUnit()

        uri = f"PYRO:ProxyFactory@{host}:{port}"
        Factory = rstrata.ProxyFactory(uri=uri)
        proxyDU = Factory.create(objNDU, **kwargsDU)
        assert_frame_equal(proxyDU.process_df(), localDU.process_df(), check_names=False, check_dtype=False)
        
        # Test series comparison
        remote_series = proxyDU.process_series()
        local_series = localDU.process_series()
        assert remote_series.equals(local_series)

    @requires_rpc_server
    def test_dataGroup_multiple_inheritance(self):
        localDG = MyNewDataGroup(baseDir, testN=testN)

        uri = f"PYRO:ProxyFactory@{host}:{port}"
        Factory = rstrata.ProxyFactory(uri=uri)
        proxyDG = Factory.create(objNDG, **kwargsDG)

        for local_df, remote_df in zip(localDG.gen_DataFrame(nc=MAX_NC), proxyDG.gen_DataFrame(nc=MAX_NC)):
            assert_frame_equal(local_df, remote_df, check_names=False, check_dtype=False)

        for local_df, remote_df in zip(localDG.gen_DataFrame(nc=1), proxyDG.gen_DataFrame(nc=1)):
            assert_frame_equal(local_df, remote_df, check_names=False, check_dtype=False)

        assert all([local == remote for local, remote in zip(localDG.Comp.func_override(nc=1), proxyDG.Comp.func_override(nc=1))])

        # multiple inheritance DataFrames
        for local_df, remote_df in zip(localDG.process_df(nc=MAX_NC), proxyDG.process_df(nc=MAX_NC)):
            assert_frame_equal(local_df, remote_df, check_names=False, check_dtype=False)

        for local_df, remote_df in zip(localDG.process_df(nc=1), proxyDG.process_df(nc=1)):
            assert_frame_equal(local_df, remote_df, check_names=False, check_dtype=False)

        # multiple inheritance Series
        for local_s, remote_s in zip(localDG.process_series(nc=MAX_NC), proxyDG.process_series(nc=MAX_NC)):
            assert local_s.equals(remote_s)

        for local_s, remote_s in zip(localDG.process_series(nc=1), proxyDG.process_series(nc=1)):
            assert local_s.equals(remote_s)

        ### parallel arrays and nc pass through
        if nc_pass_test:
            assert all([
                local == remote for local, remote in zip(
                    proxyDG.parallel_method(parallelDUInput, ncPass=True, nc=MAX_NC),
                    localDG.parallel_method(parallelDUInput, ncPass=True, nc=MAX_NC)
                )
            ])
        assert all([
            local == remote for local, remote in zip(
                proxyDG.parallel_method(parallelDUInput, ncPass=False, nc=MAX_NC),
                localDG.parallel_method(parallelDUInput, ncPass=False, nc=MAX_NC)
            )
        ])

        ## test get_DataUnit()
        proxyDU = proxyDG.get_DataUnit(0)
        localDU = localDG.get_DataUnit(0)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
        assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)

        # multiple inheritance
        assert_frame_equal(proxyDU.process_df(), localDU.process_df(), check_names=False, check_dtype=False)
        assert proxyDU.process_series().equals(localDU.process_series())

        if Pyro5.api.config.PICKLE_ENABLE:
            Pyro5.api.config.SERIALIZER = "pickle"
            proxyDU = proxyDG.get_DataUnit(0)
            assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)
            assert_frame_equal(proxyDU.gen_DataFrame(), localDU.gen_DataFrame(), check_names=False, check_dtype=False)

            # multiple inheritance
            assert_frame_equal(proxyDU.process_df(), localDU.process_df(), check_names=False, check_dtype=False)
            assert proxyDU.process_series().equals(localDU.process_series())
            Pyro5.api.config.SERIALIZER = "serpent"

    @requires_rpc_server
    def test_factory(self):
        """Make sure factory is running with terminal command 'dmanage-factory'"""
        uri = f"PYRO:ProxyFactory@{host}:{port}"
        Factory = rstrata.ProxyFactory(uri=uri)

        ######    security    #######
        insecureObj = "os"  # loading this module
        with pytest.raises(Exception):
            Factory.create(insecureObj, **kwargsDU)
            
        # check backend
        assert "fork" == Factory.get_parallel_start_method()
        assert "multiprocessing" == Factory.get_parallel_backend()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--pdb"])
    
    # t0 = time.perf_counter()
    # test = TestAllLocal()
    # test.test_expose_all()
    # test.test_dataUnit_proxy()
    # test.test_dataGroup_proxy()
    # test.test_dataUnit_multiple_inheritance()
    # test.test_dataGroup_multiple_inheritance()
    # test.test_factory()
    # print(f"\nFinished in {time.perf_counter() - t0:0.2f} seconds")
    
    #localDU = MyDataUnit(dataPath)
    
    # # comps = rstrata.get_components(localDU)
    # # print(comps)
    # uri = "PYRO:ProxyFactory@{host}:%s"%port
    # Factory = rstrata.ProxyFactory(uri=uri)
    
    # proxyDU = Factory.create(objDU,**kwargsDU)
    # kwargsDU = {'dataPath':'path2.test'}
    # proxyDU2 = Factory.create(objDU,proxy_reload=True,**kwargsDU)
    
    
    # Pyro5.api.config.SERIALIZER = "pickle"
    
    # localDG = MyDataGroup(baseDir,unitType='test')
    # uri = "PYRO:ProxyFactory@{host}:44444"
    # Factory = rstrata.ProxyFactory(uri=uri)
    
    # proxyDG = Factory.create(objDG,**kwargsDG)
    # a = localDG.parallel_method(parallelDUInput,ncPass=True,nc=MAX_NC)
    # b = proxyDG.parallel_method(parallelDUInput,ncPass=True,nc=MAX_NC)
    
    # proxyDU = proxyDG.get_DataUnit(0)
    # DF = proxyDG.gen_DataFrame()
    
    