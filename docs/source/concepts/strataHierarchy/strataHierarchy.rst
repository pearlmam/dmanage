Strata Hierarchy
================

The strata hierarchy methodology provides a coding structure for your projects so that simple data processing methods can be applied to all experimental/simulation runs easily. A diagram showing how each level relates to the others is shown below. 

.. figure:: 
   /figures/diagrams/dataHierarchy3.png

Advantages
----------

The strata hierarchy allows researchers to focus on processing their data rather than developiong the boiler plate code to apply these methods to their entire dataset. Practically what this means is that the users develop their own personal DataUnit and component classes. Then dmanage takes this personelized DataUnit and automatically creates a DataGroup class that applies each DataUnit method to all data units in the group. 

In a sense, the dmanage DataGroup class is a glorified for loop wrapper. It takes personalized DataUnit methods and component methods, applies them to each valid data unit, and returns a list of the results. This for loop is "glorified" because it can apply the DataUnit methods parallely and can reject invalid data that often crashes for loops. 

Implementation
--------------

The dmanage strata package dynamically wraps specified DataUnit methods with a parallel for loop during runtime. It utilizes the multiprocessing package to add the parallel processing. Note that as simple as it sounds, great care is needed in order to wrap class methods. Dmanage has found a way to achive this with relative ease, see the parallel processing tutorial to know more. 

Strata Stacking
---------------

Where each layer belongs in the hiearchy is contextual and each data layer can represent multiple hierarchial levels. For example with image processing, an image represents a data unit, a group of images represents a data group, and the group of images is one component of your experimental run. In this way you can have more than 3 layers by stacking them. 


Usage
-----

See the :ref:`data hierarchy tutorial` tutorial.


.. toctree::
   :maxdepth: 2
   
   components 
   dataunit
   datagroup





