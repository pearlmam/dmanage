Data Hierarchy
==============

The hierarchy methodology provides a coding structure for your projects so that simple data processing methods can be applied on database level to all experimental/simulation runs.

.. figure:: 
   /figures/diagrams/dataHierarchy2.png

Usage
-----

.. code: python
   from dmanage import make_data_unit
   from dmanage import make_data_group
   
   class UserDataUnit:
       pass
       

This provides an overview of the data hierarchy, but sometimes an example can explain how this works. See the :ref:`data hierarchy tutorial` tutorial.


.. toctree::
   :maxdepth: 2
   
   components 
   dataunit
   datagroup





