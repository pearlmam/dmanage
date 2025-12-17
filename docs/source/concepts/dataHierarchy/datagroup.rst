Data Group
==========

This comprises of multiple data units. This can be considdered a simulation or experimental sweep or a group of data units. 

DataGroup Class
---------------

This is how ``dmanage`` deals with data groups. By using a properly defined ``UserDataUnit`` class and setting the inheritance hierarchy properly, the ``DataGroup`` inherited methods and component methods are wrapped so that they are applied to all data units in the data group. Properly formatting the ``UserDataUnit`` class and inheritance is important to make this work, see :ref:`dataunit-requirments`.

Automatic DataUnit Method Wrapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The automatic wrapping of ``DataUnit`` and component methods utilizes Python attribute access methods, passing methods around like objects, and the ``DataUnit`` ``load()`` method, see section on load???






