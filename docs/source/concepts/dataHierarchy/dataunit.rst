Data Unit
=========

This represents a single run or experiment, and is comprised of all the relevant data components. 

DataUnit Class
--------------

This is how ``dmanage`` deals with data units and is comprised of the component classes. A well-developed ``DataUnit`` contains all the information about a data unit it needs to process the data robustly.

.. _dataunit-requirments:

DataUnit Requirements (For use with DataGroup)
----------------------------------------------

* ``isValid()``: this is needed so that the DataGroup class can search and find valid data units.
* ``__init__(datapath,???)``: This is needed to instantiate the class on the specific data unit.
* The ``UserDataUnit`` class must inherit from the ``dmanage`` ``DataUnit`` class. 
   
   * Need to figure out if I want the user to inherit from a assembler or not.


Adding dmanage Functionallity
-----------------------------

Blah blah blah. 
