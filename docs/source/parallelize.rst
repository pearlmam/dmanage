Parallelize
===========

dfmethods has wrappers to make methods run parallely. 

For example, the ``dmanage.dfmethods.parallelize_iterator_method()`` wraps an iterator method with the parallel implementation.

An itorator method is a function that represents one iteration. The following is an add function that takes two args.

.. code-block:: python

   def add(arg0,arg1):
       return arg0 + arg1
   
.. testcode::

   print("Hello, world!")

.. testoutput::

   Hello, world!
   
.. doctest::

   >>> print("Hello, world!")
   what????
   
Traditional Approach
--------------------
Traditionally,to make this parallel, we first must loop this function.

.. code-block:: python

   def loopedAdd(args0,args1):
       result = []
       for arg0,arg1 in zip(args0,args1):
           result = result + [add(arg0,arg1)]
       return result
   
is this good?


