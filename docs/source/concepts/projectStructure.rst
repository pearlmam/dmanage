Project Structure
=================

There are a few primary considerations what to include and the structure of your project.

* Only project specific code belongs in the project! Any code that can be used for other projects belongs in their own project. This way, common functions can be utilized for all your projects that utilize the same tools.

* Only code based files belong in the structure? Code based files work well with subversion and git, binary files do not. That being said, simulation models are often binary! Where to put these?! Also, experimental code like LabVIEW, where to put this? The answer to this question is most likely case specific and depends on the project.

* Only include the bare minimum code to make your project work. This forces you to streamline your project and makes it easy to work with. Bloated projects are difficult to work with. That being said, brainstorming can be messy sometimes, so have a place for messy code for development; find a place for the streamlined versions later.

* The example structure here can be further subdivided as needs progress. Code should be split into multiple files or directories as their function becomes more specialized. Files with 1000 lines or more should probably be split. 

Two structures are given: a minimal and a full. First, the minimal structure is given because simple code deserves a simple structure. As the project evolves, this minimal structure should be upgraded to the full structure.

Minimal Structure
-----------------

The bare minimal structure is shown below (just to get started). Data is generated manually, testing code integrety is performed by analysis scripts, loading data is performed by the core dataUnit.

.. code-block:: console

    $ tree myMinimalPythonProject
    myMinimalPythonProject/
    ├── analysis
    │   ├── anlysisScript1.py
    │   ├── anlysisScript2.py
    ├── core
    │   ├── dataUnit.py
    │   └── dataGroup.py
    ├── simulationModels
    │   ├── myPrimaryModel.code
    │   └── myVariantModel.code
    ├── scratch
    │   ├── developmentScript.py
    │   └── messyScriptButCool.py 
    

:core:
    Contains your DataUnit, DataGroup, and component classes. This provides the code to load data from your simulation or experiment. This code is used by analysis scripts. This code should be the cleanest and most robust. 

:analysis: 
    Contains your analysis scripts which use the DataUnit and DataGroup classes. The analysis directory is the place to put streamlined codes for specialized analysis. For example code that generates plots for publication can go here. This code should remain reletively untouched, except for the inputs, because the code is mostly finalized and robust. Generally, codes under active development should NOT go here but in the scratch directory. These analysis scripts are ment to be robust so that they can process data daily without errors. 
  
:simulationModels:
    There are a few different options on where to put the simulation model code itself depending on whether it is python based, project-only code, or multi-project based. Project focused models should probably go here. Multi-project models shared between multiple projects probably deserve their own project. Note that it is better to have one simulation model with multiple modes of operation rather than multiple simulation models with single modes of operation. The advantage of a using a single multi-mode model is that all modes of operation use an identical base (geometry, algorithms, etc.), whereas the base in multiple single-mode models can deviate from eachother due to the nessecity to micromanage the code base in each model; bug fixes in one model must be implemented in all models. The disadvantage of a single multi-mode model is code complexity and length.

:scratch:
    This is the place for code development. Don't be afraid to get messy. Just be mindful to eventually streamline scratch code into the primary project.

Full Structure
--------------

The fully developed structure is shown below. Code is more specialized.

.. code-block:: console

    $ tree myFullPythonProject
    myFullPythonProject/
    ├── analysis
    │   ├── anlysisScript1.py
    │   ├── anlysisScript2.py
    ├── core
    │   ├── dataUnit.py
    │   └── dataGroup.py
    │   └── component1.py
    │   └── component2.py
    └── docs
    │   ├── build
    │   ├── source
    └── dispatch
    │   ├── dispatch.py    
    │   ├── jobSubmit.py
    │   ├── config1.py
    │   ├── config2.py
    ├── simulationModels
    │   ├── myPrimaryModel.code
    │   └── myVariantModel.code
    ├── scratch
    │   ├── developmentScript.py
    │   └── messyScriptButCool.py
    ├── tests
    │   ├── data
    │   │   ├── testData.data
    │   ├── test_core.py
    │   └── test_analysis.py
    │   └── test_jobSubmit.py    
    
    
:core:
    Contains your DataUnit, DataGroup, and component classes. This provides the code to load data from your simulation or experiment. This code is used by analysis scripts. This code should be the cleanest and most robust. 


:analysis: 
    Contains your analysis scripts which use the DataUnit and DataGroup classes. The analysis directory is the place to put streamlined codes for specialized analysis. For example code that generates plots for publication can go here. This code should remain reletively untouched, except for the inputs, because the code is mostly finalized and robust. Generally, codes under active development should NOT go here but in the scratch directory. These analysis scripts are ment to be robust so that they can process data daily without errors. 

:dispatch:
   Data generation code goes here. In this example, dispatch.py contains code to run a dispatch scheduler like PBS ``qsub`` or ``dmanage.dispatch``. jobSubmit.py script contains the code to submit simulation jobs to the simulation software. This automates data generation rather than running each simulation run manually. The jobSubmit.py code is only for this project, and drives the simulation code to generate data for this project. config1.py and config2.py contain specific default parameter values for the different types of simulations; this is useful for setting up different configureations using the same simulation model.
   
:simulationModels:
    There are a few different options on where to put the simulation model code itself depending on whether it is python based, project-only code, or multi-project based. Project focused models should probably go here. Multi-project models shared between multiple projects probably deserve their own project. Note that it is better to have one simulation model with multiple modes of operation rather than multiple simulation models with single modes of operation. The advantage of a using a single multi-mode model is that all modes of operation use an identical base (geometry, algorithms, etc.), whereas the base in multiple single-mode models can deviate from eachother due to the nessecity to micromanage the code base in each model; bug fixes in one model must be implemented in all models. The disadvantage of a single multi-mode model is code complexity and length.

:scratch:
    This is the place for code development. Don't be afraid to get messy. Just be mindful to eventually streamline scratch code into the primary project.

:tests:
    This is the place to test your code. Changes to your code can have unintended consequences; tests ensure your code is robust. Test data should be minimal. Test data should probably NOT go into the git repository to keep it minimal. Consider puting methods to generate test data here that could be included in the git repository. Tests can take a bit of time to set up, but they save time and heartache overall. Test your code after every change. 

:docs:
    Documentation goes here. D-Manage uses sphinx_ for its document generation. See the :ref:`Documentation` section for more info. 



