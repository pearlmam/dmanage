# DManage
This is a Python package for generating, organizing, and processing data. This package can be used with any simulation software with proper drivers.

## Philosophy
Create a Data Directory (DD) object that can see all simulation data from one run. This can load 1D, 2D, 3D, nD data into pandas DataFrames. This DD object uses the appropriate simulation specific loaders to generate this DD object. Loaders use a specific structure that can be developed for any simulation software.The DD object can also generate summaries of the data in spreadsheets for a quick summary of the relevant data. A user can create a model specific DD object (MDD) that inherits from the DD object where the user can write their model relevant methods. 

A Sweep Data Directory object (SDD) can see all simulation data from multiple runs. This can load 1D,2D,3D,nD data from all Data Directories to generate a 2D, 3D,4D,(n+1)D pandas DataFrames. Users can create a model specific SDD object (MSDD) that inherits from the SDD object where the user can write their model relevant methods. Another goal of this is to create a framework where MSDD methods will have access to any MDD methods where the MSDD object can iterate over all Data Directories and apply the MDD method. The SDD object can also generate spreadsheet type summaries from the DD summaries for all data directories.

Since all the frontend data management is done with pandas DataFrames, DataFrame methods (dfm) are developed and used to facilitate much of the processing, conversion, and plotting. These can be used by themselves are used in conjunction with the DD and SDD objects. 

Organization of the data should attempt to use proper naming conventions; however the ultimate goal may make naming conventions less necessary. Right now plots are saved in a folder structure to be viewed with a file explorer. This requires user readable naming conventions. With the eventual visualization package, the data organization will be performed through  DataFrames and the file structure will be managed on the backend. However, user readable file structure may help with debugging and give users options for personal data management. The naming convention separates variable definitions with underscores '_', and variable names are equated to there values by dashes '-', see example below. The naming conventions follow general guidelines (need link) of characters NOT to use, like '/', '?', '=',etc. 

```
descriptor_var1-value1_var2-value2_var3-value3.extension
```

Data generation is also an important aspect to this project. Currently it is not included because it is specific to VSim and only generates parameter sweeps. There are other optimization options that probably generate data better. They not only do parameter sweeps but optimization "sweeps" that could be more versitile and useful. Right now openMDAO might be the best option for this and this project will utilize it in some way. 

Eventually data generation and data analysis will feed into eachother for efficient data generation and visualization. This offloads the data organization tasks from the user so they can focus on analysis. 




## Development
create a virtual environment and create an editable install

### In Anaconda 
create an environment, install pip, and then install the editable package

```
conda create -n dmanage
conda activate dmanage
conda install pip
pip install -e <path/to/dmanage>
``` 

to see the environment in Spyder, v6 requires spyder-kernels==3.0.

```
conda activate dmanage
pip install spyder-kernels==3.0.*
```

