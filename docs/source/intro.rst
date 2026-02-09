
Introduction
============

D-Manage is a Python package, a methodology, and a community!

* D-Manage demands easier data management
* D-Manage demands personalized data management
* D-Manage demands community data management

.. note::
   This project is in the beginning stage of development. Expect non-optimized code (help me optimize!), possible python environment issues (help me test), misspelled words, and beware of code refactoring upon new releases. 

D-Manage as a Python Package
----------------------------

The dmanage_ open source Python package is focused on data management for STEM researchers. The package requires following the D-Manage Methodology; if these methodologies and standards are followed,

this package provides:

* Automatic and parallel application of user defined data run methods to the entire data sweep: see data hierarchy
* Caching methods to store high-cost processed data in RAM or the drive for use in other methods
* Metadata methods to organize and interpret processed data
* Algorithms for signal processing, coordinate transformation, and more
* Data Plotting tools 
* Data visualization interface, IN DEVELOPMENT
* Server interface to run your project remotely as if it was local, IN DEVELOPMENT
* Creating databases from experimental and simulation files, IN DEVELOPMENT
* Data refactoring methods to help homogenize your data, IN DEVELOPMENT 
* Community developed plugins to interface with common software and datatypes, IN DEVELOPMENT

D-Manage as a Methodology
-------------------------

There are many aspects to the philosophy, but the crux of it is based on the data hierarchy. The hierarchy currently consists of two levels: the data unit and data group levels. Usually, the data unit represents one simulation/experimental run, but it can be defined in any way that suites the problem. The data group consists of multiple data units. Usually, the data group represents simulation/experimental sweeps. The D-Manage approach allows users to focus on processing the data unit, and dmanage automatically can deploy the methods to the entire data group efficiently. Other aspects of the philosophy focus on best practices and tools/components to aid in processing data efficiently, like parallel processing, caching data, and remote data access. The basics steps for the methodology are given below.

#. Generate Data

   Generate the data and store following D-Manage guidelines. The actual data of the unit can be a file or directory that contains the data. 

#. Create DataUnit

   Create a DataUnit (DU) object that can read and process all simulation/experimental data from one run. The user develops this code for their specification. D-Manage provides best practices and components to help make the DataUnit object.

#. Create DataGroup

   Use dmanage to convert the DataUnit into a DataGroup object automatically. Now the DataGroup object can identify all data units within the directory scope, apply DataUnit methods to each unit, and collect the results in one place. In this way, access to the raw data is readily available and a summary of all the data can be generated for application of machine learning methods.  


D-Manage as a Community
-----------------------

This is a place to discuss and debate the best practices for data management! By following the D-Manage methodology, understanding shared personal projects becomes easier. Researchers are often solving the same data management problems independently from each other, and each solution is unique. Not all solutions are robust or expandable to bigger datasets. Here the community can share projects and algorithms following the D-Manage methodology and determine the best technique for their applications.

This documentation also discusses programming issues common with scientific research. The tutorials discuss solutions to these issues from traditional, D-Manage methodological, dmanage package approaches. 


Who is this package for?
------------------------

This package is useful for anyone who needs to plot and analyze data! This package is especially useful for those who run many experiments and/or simulations and need to plot or process the all the data.

This package is also useful for acquiring or sharing data processing algorithms from their field of study. The standards used in this project provide a way to easily communicate with the community!

This package is useful for anyone who interacts with a server and needs to process data remotely. The dmanage_ server interface leverages RPC python packages to interact with your data as if it was local.

This package is useful for anyone interested in package development. This documentation is focused on not only on the package features themselves, but on how to contribute to the project itself! This includes how to setup, document, and develop packages.






