To Do
=====

This lists out some tasks that need completion


Near Term
---------

Data Hierarchy Examples
^^^^^^^^^^^^^^^^^^^^^^^
Add some example projects that use the D-Manage methodology. Also document these projects. The organization should allow for user-based code and documentation. I want to set a standard for organization and documentation for projects so they can be easily communicated and understood.

Concatenation
^^^^^^^^^^^^^
Need to develop common concatenate functions. For example, ``get_scalars()`` returns a dict of the variable name keys and the scalar values. When wrapped with the DataGroup, it returns a list of these dicts. We want a the variable key with a list or array of values.

We also might need a concatenate scheme for DataFrames. We shall see as we go.

Document: load() Method
^^^^^^^^^^^^^^^^^^^^^^^
This method instantiates the self object. Each level in the hierarchy has its load() method. The child method uses ``super().load()`` to access the parent ``load()`` method. Example: the ``DataGroup`` class needs to wrap its ````DataUnit`` parent methods with a looped ``DataUnit`` method. This uses ``inheritance_level()`` to determine if the ``super().load()`` method is the correct level to call ``load()``.

Anyway, Document this and develop a tutorial for this methodology. Also look into using an integer level rather than a string level. This way, N number of levels can be used.


Change Name to DManage?
^^^^^^^^^^^^^^^^^^^^^^^
Yup? NO?

Data File Types
^^^^^^^^^^^^^^^
Create a tutorial about file types: binary and ASCI files. Discuss what H5 and csv files are and how to create them. Discuss the term 'delimators'. Advantages and disadvantages.

Summary Component
^^^^^^^^^^^^^^^^^
Define the summary component for creating summary files

Cacheing Data
^^^^^^^^^^^^^
Develop soft and hard cache components. Create a tutorial for it. 

Long Term
---------

Server
^^^^^^
Right now interacting with a server is difficult. Right now run a server script locally, which sends all sub-project files along with a runscript, then runs the script on the server through paramiko. This requires the server script to pass the server info to the run script and run it. This is annoying because I need to edit both the server and run scripts. 

This implementation might be good for running simulations, but needs to be streamlined...

Also, I need a way to run scripts on the server as if they were local: an RPC implementation.

I have to deploy the dmanage_ package if I am working with dmanage; I'm kind of okay with this because the dmanage_ package should be static. Currently I have a deploy script which works rather well, But I have to remember to run it first...

Visualization
^^^^^^^^^^^^^
Develop a Python based visualization tool. This could simply visualize DataUnit components but also DataGroup plots and query specific DataUnits from the DataGroup plot. This would help quickly understand outliers, or questionable data, and understand the DataGroup. 

Creating Databases
^^^^^^^^^^^^^^^^^^
This seems like something people would be interested in. We have all these DataUnits and DataGroups and we can create a database to easily access the data...

Data Refactoring
^^^^^^^^^^^^^^^^
I already developed a way to "refactor" data from the DataUnit side, But I should probably develope ways to actually refactor data. I can probably develop a method to refactor metadata and csv files. Other data? Maybe h5 files...?

Drivers
^^^^^^^
I am really interested in using openMDAO or similar for running my simulations. The submit job implementation is okay, but I manually deal with the subprocess and terminal output. Maybe there is a better way.


