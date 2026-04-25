
 *Currently in pre-release stage. An OSI-approved license (most likely Apache 2.0 or MIT) will be chosen before the first official release.* 

Online documentation: https://dmanage.readthedocs.io/

D-Manage
========

This is a Python package for generating, organizing, and processing data. This package offers many useful features to anyone who processes data, but it is most useful for those who wish to create a database from simulation or experimental data. By following the D-Manage methodology, this package offers:

* Automatic and parallel application of user defined data run methods to the entire data sweep
* Caching methods to store high-cost processed data in RAM or the drive for use in other methods
* Metadata methods to organize and interpret processed data
* Algorithms for signal processing, coordinate transformation, and more. (**numpy**, **Pandas**, Polars, XArray, PyArrow) [#f1]_
* Data Plotting tools 
* Data visualization interface, IN DEVELOPMENT
* Server interface to run your project remotely as if it was local, IN DEVELOPMENT
* Creating databases from experimental and simulation files, IN DEVELOPMENT
* Data refactoring methods to help homogenize your data, IN DEVELOPMENT 

.. [#f1] Algorithms attempt to be datatype agnostic, where the same api can be used for numpy, Pandas, Polars, XArray, and PyArrow. This allows for easy code sharing and quick benchmarking. Currently only Numpy and Pandas are supported.

Philosophy
----------

There are many aspects to the philosophy, but the crux of it is based on the data hierarchy. The hierarchy currently consists of three levels: component, unit and group levels. Usually, the data unit (the middle level) represents one simulation/experimental run, but it can be defined in any way that suites the problem. The data unit consists of data components (the lowest level), and those represent different parts of your unit like images, waveforms, or tables, for example. The data group consists of multiple data units. Usually, the data group represents simulation/experimental sweeps. The D-Manage approach allows users to focus on processing the data unit and components, and dmanage automatically can deploy the methods to the entire data group efficiently.

Other aspects of the philosophy focus on best practices and tools/components to aid in processing data efficiently, like parallel processing, caching data, metadata, visualization, and remote data access.

Basic Project Procedure
-----------------------

Generate Data
^^^^^^^^^^^^^

Generate the data and store following D-Manage guidelines. The actual data of the unit can be a file or directory that contains the data. 

Create Components
^^^^^^^^^^^^^^^^^

Create component objects to read and analyse specific parts of your data. These components may already exist for your application. A list of community developed components can be found in a *to-be-determined* location.  

Create DataUnit
^^^^^^^^^^^^^^^

Create a DataUnit (DU) object that can read and process all simulation/experimental data from one run. The user develops this code for their specification. D-Manage provides best practices and tools to help make the DataUnit object.

Create DataGroup
^^^^^^^^^^^^^^^^

Use dmanage to convert the DataUnit into a DataGroup object automatically. Now the DataGroup object can identify all data units within the directory scope, apply DataUnit methods to each unit, and collect the results in one place. In this way, access to the raw data is readily available and a summary of all the data can be generated for application of machine learning methods.  

Data Visualization
------------------

Eventually data generation and data analysis will feed into each other for efficient data generation and visualization. This offloads the data organization tasks from the user so they can focus on analysis. 


Install
=======

The package is available in PyPi::

        pip install dmanage

Basic Use
---------

Follow the tutorials in the documentation. Use the template to create your first DataUnit and DataGroups.

Remote Computing
----------------

The dmanage package utilizes Pyro5 to implement remote procedure calls (RPC) to interact with servers. If your data lives on a remote server, this is the way to go! Basically, the user's data objects can be generated on the server, and the client can directly access those objects through a proxy and receive the results locally.  Of course, the network speed limits how much data that can be transferred practically, but often times results are much more compact than the raw data itself, so this works well!

This functionality is not provided by default, but is easy to enable. Install a fork of the Pyro5 project to your environment using the following command::

        pip install dmanage['Pyro5']
   
.. note::
   This Pyro5 fork adds pickle and dill serialization to Pyro5. Pickle and dill serialization is needed to transfer non-literal data types from server to client (think numpy arrays and matplotlib figures). There are serious security issues with using pickle, but it offers a huge convenience. Pickle is disabled by default, so your system is safe; however, it will be required for remote data visualization. See the pickle documentation for how to secure your system. Pandas DataFrame serialization is supported by the Pyro5 native serialization, serpent, but can become malformed if the DataFrame is complex (see serpent DataFrame serialization for more information).


Development
===========
create a virtual environment and create an editable install

Anaconda 
--------

create an environment, install pip, and then install the editable package::

        conda create -n dmanage
        conda activate dmanage
        conda install pip
        pip install -e <path/to/dmanage>

to see the environment in Spyder, v6 requires spyder-kernels==3.0::

        conda activate dmanage
        pip install spyder-kernels==3.0.*
            
Acknowledgments
===============

This project was developed at:

* Boise State University (BSU)


Much of this project was developed to support grant research. While this project was not the direct goal of these grants, development was supported by them nonetheless.

Funding of this project was supported by:

* Office of Naval Research (ONR)
   * N00014-21-1-2024

* The Air Force Office of Scientific Research (AFOSR)
   * FA9550-22-1-0434
   * FA2386-24-1-4055
   


   
