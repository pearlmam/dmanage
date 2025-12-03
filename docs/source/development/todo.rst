To Do
=====

This lists out some tasks that need completion


Plotting
--------

I often need to plot and save data. This is currently how I visualize datasets and compare. Plotting and saving data from one dataset is easy, but when platting and saving from a datagroup, I need to save the files with the metadata attached to the `savename`. This is how I do it now.

.. code-block:: python
   
   DataDir = make_data_unit(vsim.loader.VSim)
   class MyDataDir(DataDir):
      def __init__(self,folder):
          super().__init__(folder)
          self.Plot = Plot()
          
      
      def plot_histories(self,histnames,savename,saveloc=None,savetag=''):
          if saveloc is None:
              saveloc = self.resDir
          if savetag != '':
              savetag = '_' + savetag
              
          if not os.path.exists(saveloc):
              os.makedirs(saveloc)
          varname = 'emitFreq'
          freq = self.PreVars.read(varname)[varname]
          T = 1/freq/1e-9
          t0 = 450
          t1 = t0+5*T
          DF = self.Hists.read_as_df(histnames).abs()
          DFmean = DF.iloc[DF.index.get_level_values(0)>t0*1e-9].mean()
          transmission = DFmean[1]/DFmean[0]*100
          fig,ax = self.Plot.plot1d(DF)
          ax.set(xlim=(t0,t1),ylabel='Current [A]',title='transmission = %0.2d%%'%transmission)
          savename = savename + savetag + '.' + self.Plot.P.saveType
          fig.savefig(saveloc + savename, bbox_inches='tight', format=self.Plot.P.saveType)
          return fig,ax
          
   SweepDir = make_data_group(MyDataDir)
   class MySweepDir(SweepDir):
      
      def _plot_histories(self,histnames,savename,saveloc=None):
          if saveloc is None:
              saveloc = self.resDir
          print('saving in %s'%saveloc)
          for sweepDir in self.dataUnits:
              varname = 'emitFreq'
              DD = MyDataDir(self.baseDir + sweepDir)
              freq = DD.PreVars.read(varname)[varname]
              savetag = '%s-%0.1fe9'%(varname,freq*1e-9)
              
              DD.plot_histories(histnames, savename,saveloc=saveloc,savetag=savetag)
              
              
      def plot_histories(self,histnames,savename,saveloc=None,nc=1):
          plot_histories_ = parallelize_looped_method(self._plot_histories)
          plot_histories_(histnames,savename,saveloc=None,nc=1)
          
I use the savetag variable. How can I make this easier

Server
------

Right now interacting with a server is difficult. Right now run a server script locally, which sends all sub-project files along with a runscript, then runs the script on the server through paramiko. This requires the server script to pass the server info to the run script and run it. This is annoying because I need to edit both the server and run scripts. 

This implementation might be good for running simulations, but needs to be streamlined...

Also, I need a way to run scripts on the server as if they were local: an RPC implementation.

I have to deploy the dmanage_ package if I am working with dmanage; I'm kind of okay with this because the dmanage_ package should be static. Currently I have a deploy script which works rather well, But I have to remember to run it first...

Drivers
-------

I am really interested in using openMDAO or similar for running my simulations. The submit job implementation is okay, but I manually deal with the subprocess and terminal output. Maybe there is a better way.

Data Hierarchy Examples
-----------------------

Add some example projects that use the D-Manage methodology. Also document these projects. The organization should allow for user-based code and documentation. I want to set a standard for organization and documentation for projects so they can be easily communicated and understood.

Visualization
-------------

Develop a Python based visualization tool. This could simply visualize DataUnit components but also DataGroup plots and query specific DataUnits from the DataGroup plot. This would help quickly understand outliers, or questionable data, and understand the DataGroup. 

Concatenation
-------------

Need to develop common concatenate functions. For example, ``get_scalars()`` returns a dict of the variable name keys and the scalar values. When wrapped with the DataGroup, it returns a list of these dicts. We want a the variable key with a list or array of values.

We also might need a concatenate scheme for DataFrames. We shall see as we go.

Document: load() Method
-----------------------

This method instantiates the self object. Each level in the hierarchy has its load() method. The child method uses ``super().load()`` to access the parent ``load()`` method. Example: the ``DataGroup`` class needs to wrap its ````DataUnit`` parent methods with a looped ``DataUnit`` method. This uses ``inheritance_level()`` to determine if the ``super().load()`` method is the correct level to call ``load()``.

Anyway, Document this and develop a tutorial for this methodology. Also look into using an integer level rather than a string level. This way, N number of levels can be used.


Change Name to DManage?
-----------------------

Yup? NO






