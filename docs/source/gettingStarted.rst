Getting Started
===============

First install the package and take a look at the simple hierarchy example. This will familiarize yourself with the basic usage of the D-Manage package and methodology. Then take a look at the templates to get started on your own problem. If you are more interested in the algorithms provided by dmanage, then skip to the DataFrame methods section.

.. _installation:

Installation
------------

Install it using pip:

.. code-block:: console

   $ pip install dmanage

Often a python virtual environment is desired. Use Anaconda_ or venv_ to do this

.. _Anaconda: https://www.anaconda.com/download
.. _venv: https://docs.python.org/3/library/venv.html

Simple Hierarchy
----------------

The concept of the data hierarchy is described in the :ref:`concepts/strataHierarchy/strataHierarchy:Data Hierarchy` concept section. To see an example of how the data hierarchy is used, see the :ref:`tutorials/notebooks/dataHierarchy/dataHierarchy:Data Hierarchy` tutorial. This example generates the data and shows how to read and process simple csv files. This tutorial was made in Jupyter Notebooks, so you can follow along there. The pure Python package is available for download in the examples section (soon to be available). 

The basic procedure is given in the following subsections.

Generate Data
^^^^^^^^^^^^^

Generate the data and store following D-Manage guidelines. The actual data of the unit can be a file or directory that contains the data. 

Create Components
^^^^^^^^^^^^^^^^^

Create component objects to read and analyze specific parts of your data. These components may already exist for your application. A list of community developed components can be found in a *to-be-determined* location.  

Create DataUnit
^^^^^^^^^^^^^^^

Create a DataUnit (DU) object that can read and process all simulation/experimental data from one run. The user develops this code for their specification. D-Manage provides best practices and tools to help make the DataUnit object.

Create DataGroup
^^^^^^^^^^^^^^^^

Use dmanage to convert the DataUnit into a DataGroup object automatically. Now the DataGroup object can identify all data units within the directory scope, apply DataUnit methods to each unit, and collect the results in one place. In this way, access to the raw data is readily available and a summary of all the data can be generated for application of machine learning methods.  


Templates (In Development)
--------------------------

There are a few templates to use depending on the complexity of your problem. Find them here.


Examples (In Development)
-------------------------

There are example projects here. Sometimes the best way to learn is to look at examples of how others have tackled their research problems. And, who knows, someone else might have already solved your problem for you!

Standard Components (In Development)
------------------------------------

There are some standard component data objects to interface with common data types, equipment, and software packages. These are documented here. Maybe you can manage and process your data with dmanage_ and also utilize your favorite software! If the plugin doesn't exist for your software, consider helping develop one! Information about development is here.


DataFrame Methods (In Development)
----------------------------------

D-Manage has many algorithms developed by the community. These often utilize pandas_ DataFrames. The documentation for these methods is provided here. There are also some tutorials on how to use many of them.







   
