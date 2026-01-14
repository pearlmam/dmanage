DataFrame Methods
=================

D-Manage has adopted the ``pandas`` ``DataFrame`` object for most of it's data processing methods. This provides these advantages:

* Access to data manipulation methods provided by ``pandas``
* A unified input data standard for data processing functions for collaboration, communication, and sharing community algorithms


D-Manage has a subpackage ``dmanage.dfmethods`` with common processing methods for properly formatted DataFrames! These are community developed methods that use DataFrame input and process data. Many of the methods are just wrappers for common functions provided by other Python packages such at scipy_, numpy_, and matplotlib_. 

Many tutorials exist on the web for learning how to use DataFrames. There are also some tutorials here.

DataFrame Usage
---------------

The general DataFrame usage in ``dmanage.dfmethods`` utilizes the ``Index`` or ``MultiIndex`` as its "bounds" and the DataFrame columns as the data itself. This allows the data to be conceptualized as dimensional data, and the bounds to be "attached" to the data. For example a 1D dataset consisting of x and y values looks like this:

Blah blah

The 1D data is the column, and can be easily converted to a ``numpy`` array and processed. And the x-values of the data is the Index.

2D data looks like blah



