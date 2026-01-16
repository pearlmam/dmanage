To Do
=====

This lists out some tasks that need completion

Documentation
-------------

Rework Data Hierarchy Intro Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Right now the response is linearly increasing. The response should be a transfer function?

Automatic Method Wrapping
^^^^^^^^^^^^^^^^^^^^^^^^^
The ``load()`` method is depreciated because of super() limitations with multiprocess/ing and RPC. 

Parallelize Wrapping
^^^^^^^^^^^^^^^^^^^^
Rework the example to include the class based method wrapping and the advantages of it: picklable!

Possibly include what should and shouldn't be wrapped, addone is a poor candidate for multiprocessing because of simplicity and python method calling. Also discuss threading and GIL?

Data File Types
^^^^^^^^^^^^^^^
Create a tutorial about file types: binary and ASCII files. Discuss what H5 and csv files are and how to create them. Discuss the term 'delimiters'. Advantages and disadvantages.

Caching Data
^^^^^^^^^^^^
update tutorial for it to remove writing to the cache within the function, just need Cache.get() call to automatically write to cache.


Near Term
---------

Make get_DataUnit() Method
^^^^^^^^^^^^^^^^^^^^^^^^^^
In the DataGroup object, make a method to retrieve a DataUnit object to enable working directly on the data unit.
If RPC is used, this needs to return a proxy. This will help with data visualization.

Data Hierarchy Examples
^^^^^^^^^^^^^^^^^^^^^^^
Add some example projects that use the D-Manage methodology. Also document these projects. The organization should allow for user-based code and documentation. I want to set a standard for organization and documentation for projects so they can be easily communicated and understood.

Concatenation
^^^^^^^^^^^^^
Need to develop common concatenate functions. For example, ``get_scalars()`` returns a dict of the variable name keys and the scalar values. When wrapped with the DataGroup, it returns a list of these dicts. We want a the variable key with a list or array of values.

We also might need a concatenate scheme for DataFrames. We shall see as we go.


Change Name to DManage?
^^^^^^^^^^^^^^^^^^^^^^^
Yup? NO?


Caching Data
^^^^^^^^^^^^
Enhance the hard cache capabilities.

Long Term
---------

Server Drivers
^^^^^^^^^^^^^^
Job Running implementation. Right now I have a Paramiko implementation, but this requires passing script inputs and the run script is ugly and difficult to maintain. I need to implement a RPC job running service!

Using openMDAO or similar for running my simulations? I need a local driver too... could be the same as my RPC object...

Visualization
^^^^^^^^^^^^^
Develop a Python based visualization tool. This could simply visualize DataUnit components but also DataGroup plots and query specific DataUnits from the DataGroup plot. This would help quickly understand outliers, or questionable data, and understand the DataGroup. 

Creating Databases
^^^^^^^^^^^^^^^^^^
This seems like something people would be interested in. We have all these DataUnits and DataGroups and we can create a database to easily access the data...

Data Refactoring
^^^^^^^^^^^^^^^^
I already developed a way to "refactor" data from the DataUnit side, But I should probably develop ways to actually refactor data. I can probably develop a method to refactor metadata and csv files. Other data? Maybe h5 files...?



