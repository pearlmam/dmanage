Metadata
========

Metadata: data that provides information about other data

Often data is generated with respect to some input parameters. These input parameters decribe how the data was generated. This is a form of metadata. 

Why is this important?
----------------------

Often we generate multiple data files with respect to different input values. We need to correlate which data file corresponds to which input value. 


Techniques
----------

Here are some techniques to deal with metadata.

Filenameing
^^^^^^^^^^^

One way to deal with metadata is to add the relevant parameters to the filename. This has the advantage of being imeadiatly apparant of which data file corresponds with which input. This makes it quick to find your data in generic file explorers, and it organizes the files alpha-numerically so you can quickly preview through different data files. This disadvantage is long filenames.

The best way to name a file is to follow this protocol:

blah blah blah


Metadata File
^^^^^^^^^^^^^

Currently this is not implemented but it seems like another good solution. This file would contain a lookup table of unique file tags that corresponds to all the relevant metadata. The advantage is short filenames and can add all the metadata. Disadvantage is finding your data requires using the metadata file and without an easy front end solution for this, it can slow down your visualization or debuging process.



