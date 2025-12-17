Cacheing Processed Data
=======================

The concept is simple, storing data for use somewhere else. Often this data is passed around as inputs to functions, but this can be a burden to micromanage data like this. So in D-Manage, we can cache the data.

There are two places to "cache" data: 

* RAM. This volitile memory, meaning it is short term and is gone once you terminate the program. 
* Disk. This non-volitile memory, meaning it is long term and persists after the program is terminated AND even after the computer is shut down

In D-Manage, cached data stored in RAM is called *soft cache*. This is basically data stored in a component of the DataUnit. Cached data stored on the disk is called *hard cache*.

Soft Cache
----------

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
  
Here is a tutorial for how soft cahche is implemented.

Hard Cache
----------

Sometimes we need the result from ``method1()`` that takes a long time for other methods. ``method1()`` is well-validated and does not need to be re-run every time we use the result from that method. This is a perfect application for a hard cache: we can store the result on the disk for use in other methods to minimize computation time. Lets discuss some caveats:

* Data storage must be as small as possible
  
  * Sometimes the data we wish to store is large, so it should be stored efficiently

* Data writing and reading should be as fast as possible
  
  * Sometimes we need to access hard cached data many times
  
* more????

Here is a tutorial for how hard cache is implemented

