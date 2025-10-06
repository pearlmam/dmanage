# -*- coding: utf-8 -*-
#from dmanage import dfmethods as dfm
# from dmanage.dataDir import DataDir

# folder = './test_data/vsim_data/'
# DD = DataDir(folder)



from cycler import cycler
import matplotlib as mpl
import subprocess as sp
import shutil

class PlotDefs():
    def __init__(self,backEnd='TkAgg'):
        # backEnd='TkAgg'
        self.fig = 1                     # figure number
        self.labelfs = 22               # font size
        self.tickfs = 18
        self.colors = list('rbmcygk')         # line colors to cycle through
        self.ls = ['-',':','-.','--']    # linestyles to cycle though
        self.lw = 3                      # linewidth
        self.fw = 'bold'                 # fontweight
        self.saveType = 'png'
        self.axisUnits = {'t':'[ns]','x':'[cm]','y':'[cm]','z':'[cm]','phi':'[rad]','r':'[cm]','freq':'[GHz]','amp':'[arb]'}
        self.unitFactors = {'[ns]':1e9,'[cm]':1e2,'[GHz]':1e-9}
        self.setParameters()
        
        framework = mpl.cbook._get_running_interactive_framework()
        if framework == 'headless':
            #print("The currently running framework is '%s, using 'Agg' backend"%framework)
            self.backEnd = 'Agg'
            self.use(self.backEnd)
        elif framework == 'qt':
            # Cannot load backend 'TkAgg' which requires the 'tk' interactive framework, as 'qt' is currently running
            self.backEnd = 'QtAgg'
        elif framework == 'qt5':
            # Cannot load backend 'TkAgg' which requires the 'tk' interactive framework, as 'qt' is currently running
            self.backEnd = 'Qt5Agg'   
        elif backEnd in mpl.rcsetup.all_backends:
            self.backEnd = backEnd
            self.use(self.backEnd)
        else:
            print("The backend %s is not availiable, using 'Agg' instead"%backEnd)
            self.backEnd = 'Agg'
            self.use(self.backEnd)
        holoview = False
        if holoview:
            self.setup_holoview()
    
    def setParameters(self):
        # reset the font parameters here. or in __init__
        mpl.rc('axes',titleweight=self.fw,labelweight=self.fw, labelsize=self.labelfs,titlesize=self.labelfs)
        mpl.rc('font',size=self.tickfs, weight='normal')
        mpl.rc('lines',linewidth=self.lw)
        mpl.rcParams['axes.prop_cycle'] = cycler(color=self.colors)
        # mpl.rc('font', family='sans-serif')
        mpl.rc('text', usetex=False)
        mpl.rcParams['svg.fonttype'] = 'none'
    
    
    def setup_holoview(self):
        import hvplot.pandas  # noqa
        # pd.options.plotting.backend = 'holoviews'   
        hvplot.extension('matplotlib')
    
    def use(self,backEnd=None):
        if backEnd == None: backEnd = self.backEnd
        mpl.use(backEnd)
    
    def convertAxis(self,name,value,unit=''):
        if name == None: name = 'point'
        if name in self.axisUnits.keys():
            unit = self.axisUnits[name]
            if unit in self.unitFactors.keys():
                value = value*self.unitFactors[unit]
        return value,'%s %s'%(name,unit) 
    
        
    def fixEPS(self,fileName):
        # there is a boundingbox error in the eps files. the %%BoundingBox parameters are saved as floats, which epspdf doesnt like
        # this code fixes that
        
        # 'gs -q -dBATCH -dNOPAUSE -sDEVICE=bbox /media***REMOVED***FLAIR/IRthermography/data/CeO2/sample1/date-8.12.20/tempSweepMiddle/processed/tempSweep_center_avg.eps'
        newBB = sp.run(['gs', '-dNOPAUSE', '-dBATCH', '-q', '-sDEVICE=bbox', fileName] , stdout=sp.PIPE,stderr=sp.PIPE)
        newBB = newBB.stderr.decode('utf-8')
        tempName = 'temp.eps'
        with open(fileName,'r') as epsfile, open(tempName, 'w') as temp_file:
            for line in epsfile:
                if '%%BoundingBox:' in line:
                    temp_file.write(newBB)
                else:
                    temp_file.write(line)
        shutil.move('./' + tempName, fileName)
        return



P = PlotDefs()
P2 =  PlotDefs()
