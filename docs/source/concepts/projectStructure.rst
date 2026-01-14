Project Structure
=================

The ideal structure for your project is:

.. code-block:: console

    $ tree myPythonProject
    myPythonProject/
    ├── analysis
    │   ├── anlysisScript1.py
    │   ├── anlysisScript2.py
    ├── core
    │   ├── dataUnit.py
    │   └── dataGroup.py
    └── docs
        ├── build
        ├── source
    └── driver
        ├── jobSubmit.py
        ├── nonPython
            ├── LabView
    ├── loader
    │   ├── loader.py
    │   └── loaderHelper.py

            
:core:
    Contains your DataUnit and DataGroup classes. 

:loader: 
    Where user defined data loading code goes. With simple projects, this code can go directly into the core DataUnit. However, with more complicated projects, the data loading code should go here. This is especially useful for data loading code that can be used for multiple projects, such as user defined code that interacts with software API. This loader directory is separate from the core and can easily be used as a D-Manage plugin.


:analysis: 
    Contains your analysis scripts which use the DataUnit and DataGroup classes. The analysis directory is also a place to develop core methods; it is easier to develop algorithms outside a function so that you can access the entire variable space to help visualize and debug the code. 

:driver:
   Data generation code goes here. In this example jobSubmit.py script calls the simulation software to automate data generation rather than to generate each simulation run manually. Experimentalists can put and user developed code to read data from devices. Many times, the data generation code is non-python, for example LabView. In this case, the LabView code would go in the 'myPythonProject/driver/nonPython/LabView/' directory. This might not be the best, because LabView does not work well with git, and has its own subversion... We shall discuss!

:docs:
    Documentation goes here. D-Manage uses sphinx_ for its document generation. See the :ref:`Documentation` section for more info. 



