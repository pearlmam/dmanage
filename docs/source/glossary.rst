Glossary
========

This contains the definitions of important terms. Broken down into sections

 
Data Hierarchy Terms
--------------------

.. glossary::
   :sorted:
   
   data hierarchy
      This is the hierarchy used to build up the components of the data unit, the data unit itself, and then the data group.
   
   data unit
      This is the basic data that describes one simulation or experimental run. The data can be either one file or directory that contains multiple files. Sometimes a data unit is synonymous with a datapoint, but sometimes not. It also is associated with the ``DataUnit`` class.
      
   data group
      This represents a group of data units. The data is in a directory which contains multiple files or sub-directories. This can also be considered a simulation or experimental sweep. It is also associated with the ``DataGroup`` class.
      
   components
      In the data hierarchy, components are parts of the data unit. Programing wise, components are sub-classes of the ``DataUnit`` class, and are capitilized. These component classes have methods and attributes realted to one part of your data unit or provide helper methods and attributes (see ``SoftCache``).
      
   refactor
      The most common definition of refactoring is basically reorganizing the code to be cleaner, easier readable, better granular/modular, better performant, more efficient. In this project, the definition extends to reorganizing the data. 
      
   soft cache
      This is a temporary place to store processed data for use later. It is useful when multiple methods use the result for one method AND each method needs to be self-sufficient. This is accociated with the ``SoftCache`` component.
      
   hard cache
      This is a permant place to store processed data for use later. It is useful for storing the result from costly processing methods for use in other methods. This is accociated with the ``HardCache`` component.
      
   self-sufficient method
      This is a method that doesn't **require** input from another method result. The method may still use the result from another method, but it calls that method internally and is essentially transparent to the user. 
      
   robust method
      A robust method is one that can corrupted or missing data without raising an exception except when absolutely nessecary. Often times the units of a data group can have missing data components or unique unexpected data that the method can't handle. A robust method will ignore missing data and/or unexpected data so that most properly formated data units can be processed. Exceptions should only be raised if neccesary. 
      
       
   metadata
      Short definition: data about data. 
      Longer definition: it is data that describes the contents of data files of folders. It helps correlate data with other bits of data. D-Manage uses metastrings and/or matafiles to implement metadata
   
   metastring
      Strings that describe data names with their values. This is associated with the ``metastring`` module.
      
   metafile
      Files that contain a lookup table that contains the file/directory names along with the associated metadata. This is associated with the ``metafile`` module, currently NOT IMPLEMENTED.
      
   decorator
      A Python way to modify functions. It basically takes a function as an input, modifies it, and returns the modified function. In python, it uses the `@` syntax prefix directly above the function to be wrapped. In ``dmanage`` decorators are used to flag ``DataUnit`` methods for a ``DataGroup`` override.
      
      
      
Pandas Terms
------------
.. glossary::
   :sorted:

   DataFrame
      A pandas_ object that represents data with index and/or columns. Pandas_ provides efficient methods to manipulate DataFrames.
      
   Series
      A pandas_ object that represents one column of a DataFrame. I believe DataFrames inherit from Series.
      
   Index
      A pandas_ object that represents a single column index of the DataFrame or Series.
      
   MultiIndex
      A pandas_ object that represents a multiple column index of the DataFrame or Series.
      
   
      
   
