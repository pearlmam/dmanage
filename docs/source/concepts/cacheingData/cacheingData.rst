Cacheing Processed Data
=======================

Sometimes we need to use the result from ``method1()`` for ``method2()`` and ``method3()``. These other methods should be "self sufficient", but you don't want to re-run ``method1()`` multiple times. The standard way to do this is to add the result from ``method1()`` as an input to ``method2()`` and ``method3()``. This requires micromanaging of running ``method1()`` and adding it as inputs to ``method2()`` and ``method3()``, which is undesirable. Since we have a DataUnit class, why not use attributes of the class! This is one of the main reasons for using the DataUnit class in the first place. How do we go about doing this in the best way possible? First, lets discuss some caveats:

* We need to keep our instantiation of the DataUnit class simple and fast.

  * Our ``DataUnit`` class has many other methods that may not use ``method1()``, ``method2()``, or ``method3()``. So we don't want to do unessecary calculations every time we instantiate the DataUnit
  * Therefore, we can't run ``method1()`` in the ``__init__()`` method

* We want ``method2()`` and ``method3()`` to be self-sufficient.

  * We don't want to **require** running ``method1()`` before calling ``method2()`` and ``method3()``.
  * The methods should call ``method1()`` if it needs to or use the cached result.

* The cached variables should be syntactically aesthetic
  
  * the variable names should be short
  * Accessing the variables should be simple
  
* ?? Refractor proof  ??
  
  * The implementation should be consistent regardless of how its implemented
  * The organization might change as the complexity of your project increases. We don't want to have to find these variables all over?
  
Problem Description
-------------------

We have to calculate the average power during steady-state. The startup time changes from run to run, so we have to calculate the startup time beofre calculating power. We also need to find the spectrum of the signal during steady-state.
