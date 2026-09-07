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
)

baseDir = "/path/to/baseDir/"
dataPath = "file-99.test"
testN = 10
kwargsDU = {"dataPath": dataPath}
kwargsDG = {"baseDir": baseDir, "unitType": "test", "testN": testN}
MAX_NC = min(4, os.cpu_count() or 1)

parent = Parent()
comp1 = Component1()
comp2 = Component2()
comp3 = Component3()


class TestAll:
    def test_dataUnit(self):
        DU = MyDataUnit(dataPath)
        DU.gen_DataFrame()
        assert DU.Comp.func() == comp1.func()
        assert DU.parent_func() == parent.parent_func()
        assert DU.Comp.Comp.func() == comp2.func()

    def test_dataGroup(self):
        DU = MyDataUnit(dataPath)
        DG = MyDataGroup(dataPath, testN=testN)

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


if __name__ == "__main__":
    # Runs the test suite directly with pytest
    pytest.main([__file__, "-v", "-s"])

    # Optional: Manual plot calls for interactive visual inspection
    # DU = MyDataUnit(dataPath)
    # DU.plot2(tagVars='file')
    # DG = MyDataGroup(dataPath, testN=testN)
    # DG.plot2(tagVars='file', nc=MAX_NC)