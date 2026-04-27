#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 14 13:31:59 2025

@author: marcus
"""
from testObjects import MyDataUnit,MyNewDataUnit
from testObjects import MyDataGroup,MyNewDataGroup
from testObjects import Parent, Component1, Component2, Component3

import pytest
from unittest import TestCase


baseDir = '/path/to/baseDir/'
dataPath = 'file-99.test'
testN = 10
kwargsDU = {'dataPath':dataPath}
kwargsDG = {'baseDir':baseDir,'unitType':'test','testN':testN}

parent = Parent()
comp1 = Component1()
comp2 = Component2()
comp3 = Component3()

class TestAll(TestCase):
    run = True
    def _run(self):
        return self.run
    
    def test_dataUnit(self):
        DU = MyDataUnit(dataPath)
        DU.gen_DataFrame()
        assert DU.Comp.func() == comp1.func()
        assert DU.parent_func() == parent.parent_func()
        assert DU.Comp.Comp.func() == comp2.func()

    def test_dataGroup(self):
        DU = MyDataUnit(dataPath)
        
        DG = MyDataGroup(dataPath,unitType='test',testN=testN)
        assert all([all(resultDG == resultDU) for (resultDG,resultDU) in zip(DG.gen_DataFrame(), ([DU.gen_DataFrame()]*testN))])
        assert DG.Comp.func() == DU.Comp.func()
        assert DG.Comp.func_override() == [DU.Comp.func_override()]*testN
        assert DG.parent_func() == DU.parent_func()
        assert DG.parent_func_override() == [DU.parent_func_override()]*testN
        
        
        # parallel
        assert all([all(resultDG == resultDU) for (resultDG,resultDU) in zip(DG.gen_DataFrame(nc=4), ([DU.gen_DataFrame()]*testN))])
        assert DG.Comp.func_override(nc=4) == [DU.Comp.func_override()]*testN
        assert DG.parent_func_override(nc=4) == [DU.parent_func_override()]*testN
        assert DG.access_private_method(nc=4) == [DU._private_method()]*testN
        
        with pytest.raises(AssertionError):
            # components of components are not currently overridden, so this throws an error
            # when it doesn't, I will have successfully wrapped all sub components.
            assert DG.Comp.Comp.func_override() == [DU.Comp.Comp.func_override()]*testN
        assert DG.Comp.Comp.func() == DU.Comp.Comp.func()
        
        
        


if __name__ == "__main__":
    test = TestAll()
    test.test_dataUnit()
    test.test_dataGroup()
    
    DU = MyDataUnit(dataPath)
    DU.plot2(tagVars='file')
    #DU.plot3(tagVars='file')
    
    DG = MyDataGroup(dataPath,unitType='test',testN=testN)
    # DG.plot(nc=1)
    DG.plot2(tagVars='file',nc=4)
    # DG.plot3(tagVars='file',nc=1)
    
    # DG.plot(nc=1)
    
    