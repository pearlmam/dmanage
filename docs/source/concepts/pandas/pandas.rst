Pandas DataFrames
=================

Pandas_ is a Python package used to interact with data like a spreadsheet, where there are columns and headers. This framework provides many data manipulation methods that can virtually allow you to manipulate data in any way, relatively efficiently. This package is based on numpy_ so can easily utilize those methods as well. The disadvantage of pandas_ is that it requires more memory to perform operations. So while pandas_ is for "big data", it's limited to the memory on your computer. However, for truly "big data" there are other packages that mesh well with pandas_ such as dask_, more??. 

Pandas Performance
------------------

Long story short, Pandas_ is fast! However, it is slow if used improperly. See the pandas_ documentation on  `enhancing performance`_.

.. _`enhancing performance`: https://pandas.pydata.org/pandas-docs/stable/user_guide/enhancingperf.html

Pandas Advantage Over Numpy
---------------------------

The main advantage is that pandas_ manages data manipulation much easier than pure numpy_. And, don't forget, pandas_ can utilize numpy_ for calculations! Pandas_ can create a DataFrame from a numpy_ array, and attach the *dimensions* to the array as an *index*. *Dimensions* is often spatial coordinates or time, but can be anything. It is the second term in the expression "*y* vs *x*" when describing plots. 

For example, you have voltage vs time data; the *dimension* in this case is 'time', and the data is 'voltage'. In numpy_ you'd store this as two numpy_ arrays. In pandas_ you'd store it in one DataFrame. If you want to manipulate the data in anyway, in numpy_ you must manipulate both arrays and micromanage every operation. In pandas_, the data the time index is attached to the voltage data, and by manipulating one, you manipulate the other and it is automatically consistent. 

EXAMPLE HERE

Pandas Concepts
--------------- 

When to index?
MultiIndex
Unstacking and Stacking



.. toctree::
   :maxdepth: 2
   
   
   
   
