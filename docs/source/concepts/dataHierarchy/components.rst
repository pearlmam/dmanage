Components
==========

Components are basically parts of your data unit. These can be data components or helper classes. Describe what components are and how they are used.

Data Components
---------------

These are the parts of the data unit. The distinction between components can be somewhat arbitrary, but components are generally separated by how they are loaded into python. Perhaps an experimentalist generates data from an oscilloscope and spectrum analyzer; they would have two components. Perhaps a simulationist generates 1D, 2D, and 3D data from a simulation software, they would have 3 components that deal with each of the different data types. 

Component Classes
-----------------

These are associated with ``DataUnit``.

Plugin Components
^^^^^^^^^^^^^^^^^
These are user-defined component classes that can load or generate data for specific software, hardware, or special use cases.

Helper Components
^^^^^^^^^^^^^^^^^

These are component classes of your ``DataUnit`` that aid in processing. The current list of helper components ``dmanage`` provides are

* SoftCache
* HardCache
* Server (Not Implemented)



