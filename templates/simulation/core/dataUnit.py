# common packages

# necessary packages for data hierarchy
from dmanage.strata import make_data_unit,override

# optional packages for plotting and saving plots
from dmanage.ops.dfmethods import plot
from dmanage.metadata import metastring
import os

# begin data unit code
DataUnit = make_data_unit()
class MyDataUnit(DataUnit):
    """this is a simple DataUnit class
    """
    def __init__(self,unitpath):
        """open the data unit
        """
        super().__init__(unitpath)   # call parent to setup DataUnit
        self.dataUnit = unitpath
        self.saveType = 'png'
        
    def is_valid(self,dataUnit):
        """returns bool if the unit is a valid data unit. 
        
        the DataGroup.__init__() method uses this to check if the file or 
        directory is valid. This method MUST have one input.
        
        Parameters
        ----------
        dataUnit : path to the dataunit
        """
        # enter validity check code here
        return True
    
    #######  for plotting and saving figures   #########
    def gen_tag(self,tagVars,format=None):
        """ create a tag string to save plots with unique and human readable names
        """
        tagVars = metastring.parse(self.dataUnit,checkVars=tagVars)
        return metastring.compose(tagVars,format=format)    
    
    def read(self,):
        """read the data, this is for simple dataUnits, more complicated ones would likely use components
        """
        return 
    
    @override('plot')
    def plot(self,saveName=None,saveLoc=None,tagVars=['var0'],tagFormat=None,fig=1):
        """plot and save the data
        This function meshes well with the data group level for plotting data for all data units
        because each data unit generates its tag, each plot will be saved with a unique filename

        Parameters
        ----------
        saveName : TYPE, optional
            This is the basename of the filename. The default is None.
        saveLoc : TYPE, optional
            Save location. This will default to the self.resDir. The default is None.
        tagVars : TYPE, optional
            These are the variables of the data unit to include in the name. 
            These will generally be the sweep variables.
        tagFormat : TYPE, optional
            This determines the string formating of the variables. The default of None.
            uses a "smart" formating that may not be desirable
        fig : TYPE, optional
            This is a mandatory input for proper use with parallel plotting of data groups.
            This chooses the figure number of the plot, each process needs
            their own figure to prevent processes writing to the same figure.
            If multiple processes write to the same figure, random artifacts occur in the plots.
        Returns
        -------
        fig : TYPE
            DESCRIPTION.
        ax : TYPE
            DESCRIPTION.

        """
        
        if saveLoc is None:
            saveLoc = self.resDir
        os.makedirs(saveLoc,exist_ok=True) # Make sure the save folder exists
        if saveName is None:
            saveName = 'plot'
        saveTag = self.gen_tag(tagVars,tagFormat)
        DF = self.read()
        fig,ax = plot.plot1d(DF,fig=fig)
        fig.savefig('%s%s_%s.%s'%(saveLoc,saveName,saveTag,self.saveType) , bbox_inches='tight', format=self.saveType)
        return fig,ax
   
if __name__ == "__main__":
    # unit paths
    unitpath = '/path/to/dataUnit'
    
    # instantiate the data unit for testing unit arrays
    DU = MyDataUnit(unitpath)
  
