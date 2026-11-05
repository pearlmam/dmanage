#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pandas.testing import assert_frame_equal
import pytest
import os
from helpers.strata_objects import (
    Component1,
    Component2,
    Component3,
    MyDataGroup,
    MyDataUnit,
    Parent,
    MySuperGroup,
)

unitPath = "file-99.test"
groupPath = "groupDirectory"
superPath = "superDirectory"
testN = 10
kwargsDU = {"dataPath": unitPath}
kwargsDG = {"baseDir": groupPath, "unitType": "testDir", "testN": testN}
MAX_NC = min(4, os.cpu_count() or 1)

parent = Parent()
comp1 = Component1()
comp2 = Component2()
comp3 = Component3()

from dmanage.parallel import Pool # Adjust import to your dispatch module

def test_debug_start_method():
    p = Pool(1)
    print(f"\nACTIVE START METHOD: {p._ctx.get_start_method()}")
    p.close()
    p.join()


class TestAll:
    def test_dataUnit(self):
        DU = MyDataUnit(unitPath)
        DU.gen_DataFrame()
        assert DU.Comp.func() == comp1.func()
        assert DU.parent_func() == parent.parent_func()
        assert DU.Comp.Comp.func() == comp2.func()

    def test_dataGroup(self):
        DU = MyDataUnit(unitPath)
        DG = MyDataGroup(groupPath, testN=testN)

        # DataFrame list comparison
        expected_dfs = [DU.gen_DataFrame()] * testN
        for resultDG, resultDU in zip(DG.gen_DataFrame(), expected_dfs):
            assert_frame_equal(resultDG, resultDU, check_names=False, check_dtype=False)

        assert DG.Comp.func() == DU.Comp.func()
        assert DG.Comp.func_override() == [DU.Comp.func_override()] * testN
        assert DG.parent_func() == DU.parent_func()
        assert DG.parent_func_override() == [DU.parent_func_override()] * testN

        # Parallel execution checks
        for resultDG, resultDU in zip(DG.gen_DataFrame(nc=MAX_NC), expected_dfs):
            assert_frame_equal(resultDG, resultDU, check_names=False, check_dtype=False)

        assert DG.Comp.func_override(nc=MAX_NC) == [DU.Comp.func_override()] * testN
        assert DG.parent_func_override(nc=MAX_NC) == [DU.parent_func_override()] * testN
        assert DG.access_private_method(nc=MAX_NC) == [DU._private_method()] * testN

        # Unwrapped component test
        with pytest.raises(AssertionError):
            assert DG.Comp.Comp.func_override() == [DU.Comp.Comp.func_override()] * testN

        assert DG.Comp.Comp.func() == DU.Comp.Comp.func()
    
    def test_superGroup(self):
        SG = MySuperGroup(superPath, testN=testN)
        DG = MyDataGroup(groupPath, testN=testN)
        expected_result = [DG.gen_DataFrame()]*testN
        result = SG.gen_DataFrame()
        assert len(result) == len(expected_result)
        for resultSG, resultDG in zip(result, expected_result):
            assert len(resultSG) == len(resultDG)
            for dfSG, dfDG in zip(resultSG, resultDG):
                assert_frame_equal(dfSG, dfDG, check_names=False, check_dtype=False)

if __name__ == "__main__":
    # Runs the test suite directly with pytest
    pytest.main([__file__, "-v", "-s"])

    # Optional: Manual plot calls for interactive visual inspection
    # DU = MyDataUnit(unitPath)
    # DU.plot2(tagVars='file')
    # DG = MyDataGroup(groupPath, testN=testN)
    # DG.plot2(tagVars='file', nc=MAX_NC)