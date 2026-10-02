Components
==========

Components are basically parts of your data unit. 

Data Components
---------------

These are the parts of the data unit. The distinction between components can be somewhat arbitrary, but components are generally separated by how they are loaded into python. Perhaps an experimentalist generates data from an oscilloscope and spectrum analyzer; they would have two components. Perhaps a simulationist generates 1D, 2D, and 3D data from a simulation software, they would have 3 components that deal with each of the different data types. 

Component Classes
-----------------

These are classes that are attached to your ``DataUnit`` as attributes. Each component class loads, processes, and visualizes ONE data component. The first advantage of using component classes is code separation: instead of having one behemoth of a ``DataUnit`` where code is difficult to find, you have multiple places for speaciallized code to make it easier to find. Another advantage is code re-use: speciallized component classes can be used for multiple similarly formated data components.

Usage
-----

Each component class must have ``__init__()`` and ``is_valid()`` methods defined. 

``__init__()`` generally will have one argument that represents the path to the data component. This method sets up the instantiated class with all relevant information to access and process the data component. This makes the component class self sufficient so it can tell you anything you want to know about the data component.

``is_valid()`` checks whether the data component is valid or not. This provides a way for the data unit layer to check if this data component exists and is valid so that one missing or bad data component doesn't crash the processing of other valid data components. This should be a class or static method because the data must be valid in order to instantiate the component class. Attempting to instantiate a component class on invalid data will cause an exception. You may want to use this method inside ``__init__()`` to escape without exception if one attempts to instantiate a component class on invalid data.






