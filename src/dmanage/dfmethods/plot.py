# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import matplotlib as mpl
if mpl.cbook._get_running_interactive_framework() == 'headless':
    mpl.use('agg')
    mpl.rcParams['path.simplify'] = True
import matplotlib.pyplot as plt
from tabulate import tabulate
from matplotlib.widgets import Slider, Button,CheckButtons
from cycler import cycler
import warnings as warn
import subprocess as sp
import shutil


from dmanage.dfmethods.convert import multiIndex2Index,numpy2DF,DF2Numpy,rotateCart

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
        
        # This doesnt work for some reason 
        '''
        framework = mpl.cbook._get_running_interactive_framework()  # returns None at the moment
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
        '''
        #self.backEnd = backEnd
        #self.use(self.backEnd)
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
    
# SHOULD THIS BE A CLASS OR NOT? I want it to have access to global plot defs...
# maybe they should be global...
class Plot():   
    warn.filterwarnings("ignore", message="Ignoring specified arguments in this call because figure with num:*") # ignore warning for fig = plt.figure(fig, figsize=figsize)
    def __init__(self,backEnd='TkAgg'):
        super().__init__()
        self.P = PlotDefs(backEnd)
        
        #self.err = DFErrorMessages()
        #print('loading DFPlotter')
    
    def drawFig(self,fig=1,option='no options availiable'):
        if not mpl.get_backend().lower() == 'agg':
            # canvas draw slows stuff down and is not needed for agg backend?
            fig.canvas.draw()
        return fig
    
    def checkFig(self,fig,figsize,clear,projection='rectilinear',subplots=(1,1)):
        # get the proper figure ref
        if type(fig) == type(None): fig = plt.figure(self.P.fig, figsize=figsize)
        elif type(fig) is int: fig = plt.figure(fig, figsize=figsize)
        else: pass
        
        # check size of fig, resize if nessecary and clear if nessecary
        # sizeCheck = (tuple(fig.get_size_inches())!=figsize))  # sometimes the figsize changes by .01
        sizeCheck = (np.abs((np.array(fig.get_size_inches())-np.array(figsize)).round(1)).max() != 0.0)
        if (clear and sizeCheck) or str(clear).lower() == 'close':
            figNumber = fig.number
            plt.close(fig)
            fig = plt.figure(figNumber, figsize=figsize)
            ax = fig.subplots(nrows=subplots[0],ncols=subplots[1],subplot_kw=dict(projection=projection))
        elif clear: 
            fig.clear()
            ax = fig.subplots(nrows=subplots[0],ncols=subplots[1],subplot_kw=dict(projection=projection))
        elif len(fig.axes) < 1:
            ax = fig.subplots(nrows=subplots[0],ncols=subplots[1],subplot_kw=dict(projection=projection))
        elif len(fig.axes) >= 1:
            gs = fig.axes[0].get_gridspec()
            # if (gs.nrows != subplots[0]) or (gs.ncols != subplots[1]):
            #     figNumber = fig.number
            #     plt.close(fig)
            #     fig = plt.figure(figNumber, figsize=figsize)
            #     ax = fig.subplots(nrows=subplots[0],ncols=subplots[1],subplot_kw=dict(projection=projection))
        else:
            # ax = fig.gca()
            ax = fig.axes
            if projection != ax[0].name: 
                print("Warning, included fig object type is '%s', yet desired projection='%s'"%(ax.name,projection))
           
        if not clear and sizeCheck:
            print('Warning: cannot resize figure without clearing the figure, ignoring figsize.')
        # ax = fig.gca()
        ax = fig.axes
        
        if len(ax) == 1:
            ax = ax[0]
        return fig,ax
    
        
    def plot1D(self,DF,fig=None,figsize=(12, 5),clear=True,subplots=(1,1),subplot=0,axType='linear',drawFig=True,convertAxis=True,**line2Dkwargs):
        if type(DF.index) == pd.core.indexes.multi.MultiIndex: DF = multiIndex2Index(DF)
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        

        projection = 'rectilinear'
        fig,axs = self.checkFig(fig,figsize,clear,projection,subplots=subplots)
        if isinstance(axs, (list,tuple)):
            ax = axs[subplot]
        else:
             ax = axs
        
        x = DF.index.values
        xlabel = DF.index.name

        if convertAxis:
            x,xlabel = self.P.convertAxis(DF.index.name,x)
        
        for i,col in enumerate(DF.columns):
            if 'label' in line2Dkwargs.keys():
                label = line2Dkwargs.pop('label')
            else:
                label = col
            y = DF[col]
            mask = np.isfinite(y)    # ignore nan values
            if axType == 'linear':
                ax.plot(x[mask], y[mask],label=label,**line2Dkwargs)
            elif axType == 'semilogx':
                ax.semilogx(x[mask], y[mask],label=label, **line2Dkwargs)
            elif axType == 'semilogy':
                ax.semilogy(x[mask], y[mask],label=label, **line2Dkwargs)
            elif axType == 'loglog':
                ax.loglog(x[mask], y[mask],label=label, **line2Dkwargs)
        # if min(x) != max(x): ax.set(xlim=[min(x), max(x)],xlabel=xlabel)
        if not mpl.get_backend().lower() == 'agg':
            fig.subplots_adjust(bottom=0.15)
        
        if drawFig:
            ax.grid(True)
            ax.legend(loc='best')
            ax.set(xlabel=xlabel)
            fig = self.drawFig(fig)
        return fig,ax
    
    def plot1Ds(self,DF,fig=None,figsize=(12, 5),clear=True,drawFig=False,**line2Dkwargs):
        if type(DF.index) == pd.core.indexes.multi.MultiIndex:
            iNames = DF.index.names
            if len(iNames)!=2: raise Exception('MultiIndex must have 2 levels to plot multiple lines')
        else: raise Exception("Index be of type MultiIndex with two levels. Use DF.set_index(['iName1','iName2'])")
        
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
        colName = DF.columns[0]
        fig,ax = self.checkFig(fig,figsize,clear)
        
        DF = DF.unstack(iNames[0])[colName]
        fig,ax = self.plot1D(DF,fig=fig,figsize=figsize,clear=clear,drawFig=False,**line2Dkwargs)
        ax.set(title=colName)
        xlabel = DF.index.name
        if drawFig:
            ax.grid(True)
            ax.legend(loc='best')
            ax.set(xlabel=xlabel)
            fig = self.drawFig(fig)
        return fig,ax
        
    
    
    def bar(self,DF,fig=None,figsize=(12, 5),clear=True,convertAxis=True,**line2Dkwargs):
        if type(DF.index) == pd.core.indexes.multi.MultiIndex: DF = multiIndex2Index(DF)
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
        
        fig,ax = self.checkFig(fig,figsize,clear)
        
        x = DF.index.values
        xlabel = DF.index.name

        if convertAxis:
            x,xlabel = self.P.convertAxis(DF.index.name,x)
        y = DF[DF.columns[0]]
        # width = (x[1]-x[0])
        width = np.mean(np.diff(x))
        ax.bar(x, y,**line2Dkwargs,width=width,edgecolor='k',linewidth=1)
        fig = self.drawFig(fig)
        return fig,ax
    
    
    def plot1DWPks(self,DF,fig=None,figsize=(12,5),subplots=(1,1),subplot=0,maxPks=10,hRatio=None,pRatio=None,height=None,xlim=None):
        if type(DF.index) == pd.core.indexes.multi.MultiIndex: DF = multiIndex2Index(DF)
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
        
        clear = True
        projection = 'rectilinear'
        fig,axs = self.checkFig(fig,figsize,clear,projection,subplots=subplots)
        if isinstance(axs, (list,tuple)):
            ax = axs[subplot]
        else:
             ax = axs
        
        DFpks,props = self.findPks(DF,maxPks=maxPks,hRatio=hRatio,pRatio=pRatio,height=height)
        fig,ax = self.plot1D(DF,fig=fig)
        ax.set(xlim=xlim)
        fig,ax = self.numScatterWChart(DFpks,fig=fig,clear=False)
        fig = self.drawFig(fig)
        return fig,axs
        
    
    def numScatter(self,DF,fig=None,figsize=(12, 5),clear=True,convertAxis=True,**line2Dkwargs):
        if type(DF.index) == pd.core.indexes.multi.MultiIndex: DF = multiIndex2Index(DF)
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        
        fig,ax = self.checkFig(fig,figsize,clear)
        
        x = DF.index.values
        xlabel = DF.index.name
        if convertAxis:
            x,xlabel = self.P.convertAxis(DF.index.name,x)
        for i,col in enumerate(DF.columns):
            y = DF[col].to_numpy()
            for j in range(0,len(y)):
                plt.text(x[j],y[j],j,fontsize=self.P.tickfs,horizontalalignment='center', verticalalignment='bottom' )
        return fig,ax
                
    def labeledScatter(self,DF,labelCol=None,fig=None,figsize=(12, 5),clear=True,subplots=(1,1),subplot=0,convertAxis=True,axType='linear',**line2Dkwargs):
        if type(DF.index) == pd.core.indexes.multi.MultiIndex: DF = multiIndex2Index(DF)
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        
        columns = list(DF.columns)
        columns.remove(labelCol)
        
        fig,ax = self.scatter(DF[columns],fig=fig,figsize=figsize,clear=clear,subplots=subplots,subplot=0,convertAxis=convertAxis,axType=axType,**line2Dkwargs)
        
        x = DF.index.values
        xlabel = DF.index.name
        if convertAxis:
            x,xlabel = self.P.convertAxis(DF.index.name,x)
        columns = list(DF.columns)
        columns.remove(labelCol)
        
        for i,col in enumerate(columns):
            y = DF[col].to_numpy()
            for j,label in enumerate(DF[labelCol]):
                plt.text(x[j],y[j],label,fontsize=self.P.tickfs,horizontalalignment='center', verticalalignment='bottom' )
        return fig,ax 
    
    def prepTextChart(self,DF,fmt=".2f"):
        # if not type(fmt) is list:
        #     fmt = [fmt]*2
        # if type(fmt) is list:
        #     if len(fmt) == 1:
        #         fmt = fmt*2
        #     if len(fmt) == 2:
        #         fmt = ['0.0f'] + fmt
        
        if not type(DF.index) is pd.core.indexes.range.RangeIndex:
            DF = DF.reset_index()
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        cols = list(DF.columns)
        for i,col in enumerate(DF.columns):
            if col in self.P.axisUnits.keys():
                unit = self.P.axisUnits[col]
                cols[i] = '%s\n%s'%(col,unit)
                if unit in self.P.unitFactors.keys():
                    DF[col] = DF[col]*self.P.unitFactors[unit]         
        DF.columns = cols
        output = tabulate(DF,floatfmt=fmt,headers="keys",tablefmt="plain",numalign="left") 
        
        return output
    
    def numScatterWChart(self,DF,fmt=[".0f",'.2f','.1f'],textPos=None,fontsize=14,fig=None,figsize=(12, 5),clear=True):
        if type(DF.index) == pd.core.indexes.multi.MultiIndex: DF = multiIndex2Index(DF)
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")

        fig,ax = self.checkFig(fig,figsize,clear)
        
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        DF.columns=['amp']
        fig,ax = self.numScatter(DF,fig=fig,figsize=(12,5),clear=False)
        if not ax.get_legend() is None:
            ax.get_legend().remove()
        # DF = DF.reset_index()['freq']   # remove the amplitude from the chart
        
        output = self.prepTextChart(DF,fmt=fmt)
        if textPos is None:
            textPos = [ (xlim[1])*.82, ylim[1]*.95]
        ax.text(textPos[0], textPos[1],output,fontsize=fontsize,horizontalalignment='left', verticalalignment='top' )
        fig = self.drawFig(fig)
        return fig,ax
    
    def scatter(self,DF,fig=None,figsize=(12, 5),clear=True,subplots=(1,1),subplot=0,drawFig=True,convertAxis=True,axType='linear',**line2Dkwargs):
        # need to add colorbar option, what should the data look like? 2D data?? probably.
        if type(DF.index) == pd.core.indexes.multi.MultiIndex: DF = multiIndex2Index(DF)
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        
        projection = 'rectilinear'
        fig,axs = self.checkFig(fig,figsize,clear,projection,subplots=subplots)
        if isinstance(axs, (list,tuple)):
            ax = axs[subplot]
        else:
             ax = axs
        # fig,ax = self.checkFig(fig,figsize,clear)
        
        x = DF.index.values
        xlabel = DF.index.name

        if convertAxis:
            x,xlabel = self.P.convertAxis(DF.index.name,x)
        for i,col in enumerate(DF.columns):
            if 'label' in line2Dkwargs.keys():
                pass
            else:
                line2Dkwargs['label'] = col
            y = DF[col]
            ax.scatter(x, y, **line2Dkwargs)
            line2Dkwargs.pop('label')
        
        if axType == 'semilogx':
            ax.set_xscale("log")
        elif axType == 'semilogy':
            ax.set_yscale("log")
        elif axType == 'loglog':
            ax.set_xscale("log")
            ax.set_yscale("log")
        
        # if min(x) != max(x): ax.set(xlim=[min(x), max(x)],xlabel=xlabel)
        xMin = min(x[x != -np.inf])
        xMax = max(x[x != np.inf])
        if xMin != xMax: 
            ax.set(xlim=[xMin, xMax])
            # ax.set_xbound(lower=min(x), upper=max(x))
            
        if not mpl.get_backend().lower() == 'agg':
            fig.subplots_adjust(bottom=0.15)
        if drawFig:
            ax.grid(True)
            ax.legend(loc='best')
            ax.set(xlabel=xlabel)
            fig = self.drawFig(fig)
        return fig,ax
   
    def scatterColor(self,DF,fig=None,figsize=(12, 5),clear=True,cbar=True,subplots=(1,1),subplot=0,drawFig=True,convertAxis=True,**line2Dkwargs): 
        """
        DF has 2 indicies for xy and intensity values for the column. Similar to pcolor
        """
        if type(DF.index) == pd.core.indexes.multi.MultiIndex:
            iNames = DF.index.names
            if len(iNames)!=2: raise Exception('MultiIndex must have 2 levels for a 2D plot')
        else: raise Exception("Index be of type MultiIndex with two levels. Use DF.set_index(['iName1','iName2'])")
        if issubclass(type(DF), pd.core.series.Series): DF = DF.to_frame()
        if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
        else: title = DF.columns[0]
        xlabel = iNames[0]
        ylabel = iNames[1]
        clabel = title
        projection = 'rectilinear'
        fig,axs = self.checkFig(fig,figsize,clear,projection,subplots=subplots)
        if isinstance(axs, (list,tuple)):
            ax = axs[subplot]
        else:
             ax = axs
        
        
        DF = DF.reset_index()
        x = DF[iNames[0]]
        y = DF[iNames[1]]
        c = DF[title]
        label = list(iNames)
        
        if convertAxis:
            x,label[0] = self.P.convertAxis(iNames[0],x)
            y,label[1] = self.P.convertAxis(iNames[1],y)
        
        cax = ax.scatter(x, y, c=c,label=ylabel,**line2Dkwargs)
        if cbar:
            cbar = fig.colorbar(cax)
            # cbar.ax.set_title(clabel)
            cbar.set_label(clabel, labelpad=0)
        else:
            cbar = cax

        if not mpl.get_backend().lower() == 'agg':
            fig.subplots_adjust(bottom=0.15) 
        
        if drawFig:
            ax.grid(True)
            ax.legend(loc='best')
            ax.set(xlabel=xlabel)
            fig = self.drawFig(fig)
        return fig,ax,cbar
        
        
    
    def tricontourf(self,DF,fig=None,figsize=(12, 5),clear=True,cmap='viridis',convertAxis=True):
        # check DF for proper format
        if not issubclass(type(DF), pd.core.series.Series): 
            if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
            else: title = DF.columns[0]
        else: title = DF.name
            
        if type(DF.index) == pd.core.indexes.multi.MultiIndex:
            iNames = DF.index.names
            if len(iNames)!=2: raise Exception('MultiIndex must have 2 levels for a 2D plot')
        else: raise Exception("Index be of type MultiIndex with two levels. Use DF.set_index(['iName1','iName2'])")
        
        fig,ax = self.checkFig(fig,figsize,clear)
        
        DF = DF.reset_index()
        x = DF[iNames[0]]
        y = DF[iNames[1]]
        z = DF[title]
        
        label = list(iNames)
        if convertAxis:
            x,label[0] = self.P.convertAxis(iNames[0],x)
            y,label[1] = self.P.convertAxis(iNames[1],y)
        
        plot = ax.tricontourf(x, y, z,cmap=cmap)

        cbar = fig.colorbar(plot,ax=ax)
        ax.set(xlabel=label[0],ylabel=label[1],title=title)
        ax.grid(True)
        if not mpl.get_backend().lower() == 'agg':
            fig.subplots_adjust(bottom=0.15)
        fig = self.drawFig(fig)
        return fig,ax,plot,cbar

    def contourf(self,DF,fig=None,figsize=(12, 5),clear=True,polar=False,cmap='viridis',convertAxis=True):
        """
        Description needed

        Parameters
        ----------
        DF : TYPE
            DESCRIPTION.
        fig : TYPE, optional
            DESCRIPTION. The default is None.
        figsize : TYPE, optional
            DESCRIPTION. The default is (12, 5).
        clear : TYPE, optional
            DESCRIPTION. The default is True.
        polar : TYPE, optional
            DESCRIPTION. The default is False.
        cmap : TYPE, optional
            DESCRIPTION. The default is 'viridis'.
        convertAxis : TYPE, optional
            DESCRIPTION. The default is True.

        Raises
        ------
        Exception
            DESCRIPTION.

        Returns
        -------
        fig : TYPE
            DESCRIPTION.
        ax : TYPE
            DESCRIPTION.
        plot : TYPE
            DESCRIPTION.
        cbar : TYPE
            DESCRIPTION.

        """
        
        # check DF for proper format
        if not issubclass(type(DF), pd.core.series.Series): 
            if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
            else: title = DF.columns[0]
        else: title = DF.name
            
        if type(DF.index) == pd.core.indexes.multi.MultiIndex:
            iNames = DF.index.names
            if len(iNames)!=2: raise Exception('MultiIndex must have 2 levels for a 2D plot')
        else: raise Exception("Index be of type MultiIndex with two levels. Use DF.set_index(['iName1','iName2'])")
        
        # open the figure properly
        if polar: projection='polar'
        else: projection='rectilinear'
        
        fig,ax = self.checkFig(fig,figsize,clear,projection)
        
        array,bounds = DF2Numpy(DF,sort_index=False)
        x = bounds[iNames[0]]
        y = bounds[iNames[1]]
        
        label = list(iNames)
        if convertAxis:
            x,label[0] = self.P.convertAxis(iNames[0],x)
            y,label[1] = self.P.convertAxis(iNames[1],y)
        if polar: 
            ax.set(title=title,ylim=[0,max(y)])
            x = np.concatenate([x,x[[0]]])
            array = np.concatenate([array,np.expand_dims(array[0,:],axis=0)],axis=0)
        else: ax.set(xlabel=label[0],ylabel=label[1],title=title)
        
        plot = ax.contourf(x,y,array.T,cmap=cmap)
        cbar = fig.colorbar(plot,ax=ax)
        
        ax.grid(True)
        if not mpl.get_backend().lower() == 'agg':
            fig.subplots_adjust(bottom=0.15)
        fig = self.drawFig(fig)
        return fig,ax,plot,cbar
   
    def pcolor(self,DF,fig=None,figsize=(12, 5),clear=True,polar=False,subplots=(1,1),subplot=0,cmap='viridis',cbarOrientation='vertical',convertAxis=True):
        
        # check DF for proper format
        if not issubclass(type(DF), pd.core.series.Series): 
            if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
            else: title = DF.columns[0]
        else: title = DF.name
            
        if type(DF.index) == pd.core.indexes.multi.MultiIndex:
            iNames = DF.index.names
            if len(iNames)!=2: raise Exception('MultiIndex must have 2 levels for a 2D plot')
        else: raise Exception("Index be of type MultiIndex with two levels. Use DF.set_index(['iName1','iName2'])")
        
        
        for iName in iNames:
            s = len(DF.index.get_level_values(iName).unique())
            if s == 1:
                print("Index level %s has 1 unique value, this is one-dimensional data, remove this level and use DFM.plot1D "%iName)
                return None, None, None, None
        # open the figure properly
        if polar: projection='polar'
        else: projection='rectilinear'
        
        fig,axs = self.checkFig(fig,figsize,clear,projection,subplots=subplots)
        if isinstance(axs, (list,tuple)):
            ax = axs[subplot]
        else:
             ax = axs
             
        array,bounds = DF2Numpy(DF,sort_index=True)
        x = bounds[iNames[0]]
        y = bounds[iNames[1]]
        
        label = list(iNames)
        if convertAxis:
            x,label[0] = self.P.convertAxis(iNames[0],x)
            y,label[1] = self.P.convertAxis(iNames[1],y)
        # used to be np.object
        if array.dtype == object: array = array.astype(float)
         
        plot = ax.pcolor(x,y,array.T,shading='auto',cmap=cmap)
        if not cbarOrientation is None: 
            if polar:
                if cbarOrientation == 'horizontal':
                    fraction=0.043
                    cbarLocation='top'
                else:
                    fraction=0.034
                    cbarLocation='right'
                # cbar = fig.colorbar(plot,ax=ax,fraction=0.038, pad=0.02)
                cbar = fig.colorbar(plot,ax=ax,fraction=fraction, pad=0.01,orientation=cbarOrientation,location=cbarLocation)
                if cbarLocation=='right':
                    cax = ax.collections[0].colorbar.ax
                    pos = cax.get_position()
                    cax.set_position([pos.x0, pos.y0*1.35, pos.width, pos.height])  # set a new position
                    cax.set_frame_on(True)
            else:
                cbar = fig.colorbar(plot,ax=ax,pad=0.02)
        else:
            cbar = None
        # cbar = fig.colorbar(plot,ax=ax)
        
        if polar: ax.set(title=title)
        else: ax.set(xlabel=label[0],ylabel=label[1],title=title)
        ax.grid(True)
        #plt.show()
        if not mpl.get_backend().lower() == 'agg':
            fig.subplots_adjust(bottom=0.15)
        fig = self.drawFig(fig)
        return fig,axs,plot,cbar
    
    
    def plot1DSlider(self,DF,fig=1,clear=True):
        if not issubclass(type(DF), pd.core.series.Series): 
            if len(DF.columns)>1: raise Exception("DF must be of type Series or of type DataFrame with one column.")
            else: title = DF.columns[0]
        else: title = DF.name
        
        array,bounds = DF2Numpy(DF)
        z = bounds[list(bounds.keys())[0]]
        dz=z[1]-z[0]
        x = bounds[list(bounds.keys())[1]]

        # The parametrized function to be plotted
        def f(t,dt,array):
            N = np.int32(t/dt)
            return array[N,:]

        # Create the figure and the line that we will manipulate
        fig,ax = self.checkFig(fig=fig,figsize=(12,5),clear=clear)
        
        line, = ax.plot(x, f(z[0],dz,array), lw=2)
        ax.set_xlabel(list(bounds.keys())[1])
        ax.set_ylim([np.amin(array), np.amax(array)])

        axcolor = 'lightgoldenrodyellow'
        ax.margins(x=0)

        # adjust the main plot to make room for the sliders
        fig.subplots_adjust(left=0.1, bottom=0.35)

        # Make a horizontal slider to control the frequency.
        axtime = fig.add_axes([0.2, 0.15, 0.60, 0.03], facecolor=axcolor)
        z_slider = Slider(
            ax=axtime,
            label=list(bounds.keys())[0],
            valmin=0.0,
            valmax=z[len(z)-1],
            valinit=z[0],
            valfmt='%0.2e',
            )
        axnext = fig.add_axes([0.6, 0.05, 0.1, 0.05], facecolor=axcolor)
        bnext = Button(axnext, 'Next')
        axprev = fig.add_axes([0.4, 0.05, 0.1, 0.05], facecolor=axcolor)
        bprev = Button(axprev, 'Previous')
        # The function to be called anytime a slider's value changes
        def update(val):
            line.set_ydata(f(z_slider.val, dz,array))
            fig.canvas.draw_idle()
            
        def nextStep(val):
            value = z_slider.val+10*dz
            if value > z_slider.valmax: 
                value = z_slider.valmax
            z_slider.set_val(value)

        def prevStep(val):
            value = z_slider.val-10*dz
            if value < z_slider.valmin: 
                value = z_slider.valmin
            z_slider.set_val(value)
        ax.set(title=title)    
        # register the update function with each slider
        z_slider.on_changed(update)
        bnext.on_clicked(nextStep)
        bprev.on_clicked(prevStep)
        buttons = [z_slider,bnext,bprev]
        # buttons must be returned so that they dont get garbage collected
        return fig,ax,buttons
    
    def plot1DSlider2(self,DF,plotVar=False,fig=1,fmt='#e',clear=True):
        if not issubclass(type(DF), pd.core.series.Series): 
            if len(DF.columns)>1 and not plotVar: 
                raise Exception("DF must be of type Series or of type DataFrame with one column.")
            elif plotVar:
                pass
            else: 
                plotVar = DF.columns[0]
        else:
            DF = DF.to_frame()
            plotVar = DF.columns[0]
        fmt = fmt.replace('%','#')
            
        DF = DF.sort_index()
        z = DF.index.get_level_values(0).unique()
        x = DF.index.get_level_values(1).unique()

        # The parametrized function to be plotted
        def fy(DF,itag):
            tag = z[int(itag)]
            out = DF.loc[tag].to_numpy()
            # print(len(out))
            return out
        
        def fx(DF,itag):
            tag = z[int(itag)]
            out = DF.loc[tag].index.get_level_values(0).to_numpy()
            # print(len(out))
            return out
            
        # Create the figure and the line that we will manipulate
        fig,ax = self.checkFig(fig=fig,figsize=(12,5),clear=clear)
        
        line, = ax.plot(fx(DF[[plotVar]],0), fy(DF[[plotVar]],0), lw=2)
        ax.set_xlabel(DF.index.names[1])
        ax.set_ylim([DF[[plotVar]].min()[0], DF[[plotVar]].max()[0]])
        ax.set_xlim([x.min(), x.max()])
        axcolor = 'lightgoldenrodyellow'
        ax.margins(x=0)

        # adjust the main plot to make room for the sliders
        fig.subplots_adjust(left=0.1, bottom=0.35)

        # Make a horizontal slider to control the frequency.
        axtime = fig.add_axes([0.2, 0.15, 0.60, 0.03], facecolor=axcolor)
        z_slider = Slider(
            ax=axtime,
            label='tag index', # ,
            valmin=0.0,
            valmax=len(z)-1,
            valinit=0,
            valfmt='%0.0i',
            )
        axnext = fig.add_axes([0.6, 0.05, 0.1, 0.05], facecolor=axcolor)
        bnext = Button(axnext, 'Next')
        axprev = fig.add_axes([0.4, 0.05, 0.1, 0.05], facecolor=axcolor)
        bprev = Button(axprev, 'Previous')
        # The function to be called anytime a slider's value changes
        def update(val):
            line.set_xdata(fx(DF[[plotVar]], z_slider.val))
            line.set_ydata(fy(DF[[plotVar]], z_slider.val))
            zval = format( z[int(z_slider.val)],fmt)
            title = '%s, %s=%s'%(plotVar,DF.index.names[0],zval)
            if 'Tcirc' in DF.columns:
                title = title + ', Tcirc=%0.2f ns'%(DF.loc[z[int(z_slider.val)],'Tcirc'].iloc[0])
            ax.set(title=title)  
            fig.canvas.draw_idle()
            
        def nextStep(val):
            value = z_slider.val+1
            if value > z_slider.valmax: 
                value = z_slider.valmax
            z_slider.set_val(value)

        def prevStep(val):
            value = z_slider.val-1
            if value < z_slider.valmin: 
                value = z_slider.valmin
            z_slider.set_val(value)
           
        # register the update function with each slider
        zval = format( z[int(z_slider.val)],fmt)
        title = '%s, %s=%s'%(plotVar,DF.index.names[0],zval)
        if 'Tcirc' in DF.columns:
            title = title + ', Tcirc=%0.2f ns'%(DF.loc[z[int(z_slider.val)],'Tcirc'].iloc[0])
        ax.set(title=title)  
        
        z_slider.on_changed(update)
        bnext.on_clicked(nextStep)
        bprev.on_clicked(prevStep)
        buttons = [z_slider,bnext,bprev]
        # buttons must be returned so that they dont get garbage collected
        return fig,ax,buttons
    
    
    def interactSweepData(self,DF,):
        pass
    
    def interactTaggedParicles(self,DF,tags=None,fig=None,figsize=(8,8),clear=True,freq=None):
        xy = ['x','y']
        projection='rectilinear'
        fig,ax = self.checkFig(fig,figsize,clear,projection)
        if tags is None:
            nums = list(DF.index.get_level_values('tag').unique())
        else:
            nums = tags
        
        # The parametrized function to be plotted
        def f(DF,num,rot=False):
            DF = DF.loc[nums[num]][xy]
            t = DF.index.values
            if rot:
                theta = -2*np.pi/3*freq*(t)
                DF = rotateCart(DF,theta,xyCols=xy)  
            # info = [xs, ys, ts, tag]
            info = [DF[xy[0]].to_numpy(),DF[xy[1]].to_numpy(),DF.index.values,nums[num]]
            return info
        
        def toggle(DF,t,rot=False):
            DF = DF.reorder_levels(['t','tag']).loc[t]
            # print(DF)
            if rot:
                theta = -2*np.pi/3*freq*(t)
                DF = rotateCart(DF,theta,xyCols=xy)
            info = [DF[xy[0]].to_numpy(),DF[xy[1]].to_numpy()]
            return info
            
        traj = f(DF,0)
        parts = toggle(DF,traj[2][0])
        
        line2, = ax.plot(parts[0], parts[1],ls='None',marker='o',color='b',ms=3)
        line, = ax.plot(traj[0], traj[1], lw=3,color='r')
        line1, = ax.plot(traj[0][0], traj[1][0],marker='o',color='k',ms=3)
        
        text = fig.text(0.7, 0.16,'temit=%0.2e\ntag=%i'%(traj[2][0],traj[3]))
        mins = DF[xy].min().to_list()
        maxs = DF[xy].max().to_list()
        ax.set(xlabel=xy[0],ylabel=xy[1],xlim=[mins[0],maxs[0]],ylim=[mins[1],maxs[1]])
        # ax.axis('equal')
    
        axcolor = 'lightgoldenrodyellow'
        ax.margins(x=0)
    
        # adjust the main plot to make room for the sliders
        fig.subplots_adjust(left=0.1, bottom=0.35)
        
        # Make a horizontal slider for time
        # axtime = fig.add_axes([0.2, 0.15, 0.60, 0.03], facecolor=axcolor)
        # t_slider = Slider(
        #     ax=axtime,
        #     label='Time',
        #     valmin=info[2][0],
        #     valmax=info[2][-1],
        #     valinit=info[2][-1],
        #     valfmt='%0.2e',
        #     )
        
        # Make a horizontal slider for time
        axtag = fig.add_axes([0.2, 0.25, 0.60, 0.03], facecolor=axcolor)
        num_slider = Slider(
            ax=axtag,
            label='Index',
            # valmin=min(nums),
            # valmax=max(nums),
            # valinit=min(nums),
            # valfmt='%0.0i',
            
            valmin=0,
            valmax=len(nums)-1,
            valinit=0,
            valfmt='%0.0i',
            )
        
        axnext = fig.add_axes([0.5, 0.15, 0.15, 0.05], facecolor=axcolor)
        bnext = Button(axnext, 'Next')
        axprev = fig.add_axes([0.3, 0.15, 0.15, 0.05], facecolor=axcolor)
        bprev = Button(axprev, 'Previous')
        axrot = fig.add_axes([0.1, 0.15, 0.15, 0.05], facecolor=axcolor)
        bprot = CheckButtons(axrot, ['rotate'])
        axparts = fig.add_axes([0.1, 0.05, 0.15, 0.05], facecolor=axcolor)
        bparts = CheckButtons(axparts, ['particles'],actives=[True])
        
        # The function to be called anytime a slider's value changes
        # def updateTime(val):
        #     line.set(ydata=info[0],xdata=info[1])
        #     fig.canvas.draw_idle()
            
        def updateNum(num):
            # print(bprot.get_status())
            info = f(DF,int(num),bprot.get_status()[0])
            line.set(xdata=info[0],ydata=info[1])
            line1.set(xdata=info[0][0],ydata=info[1][0])
            text.set(text='temit=%0.2e\ntag=%i'%(info[2][0],info[3]))
            toggleParts(bparts.get_status()[0])
            fig.canvas.draw_idle()
            
            
        def nextNum(val):
            value = int(num_slider.val)+1
            if value > num_slider.valmax: 
                value = num_slider.valmax
            num_slider.set_val(value)

        def prevNum(val):
            value = int(num_slider.val)-1
            if value < num_slider.valmin: 
                value = num_slider.valmin
            num_slider.set_val(value)
          
        def rotate(value):
            num_slider.set_val(int(num_slider.val))

        def toggleParts(value):
            num = int(num_slider.val)
            # print(num)
            # print(nums[num])
            
            t = DF.loc[nums[num]]
            
            t = t.index[0]
            if bparts.get_status()[0]:
                info = toggle(DF,t,bprot.get_status()[0])
                line2.set(visible=True,xdata=info[0],ydata=info[1])
            else:
                line2.set(visible=False)
            
            fig.canvas.draw_idle()
            
        ax.set(title='trajectories')    
        # register the update function with each slider
        num_slider.on_changed(updateNum)
        bnext.on_clicked(nextNum)
        bprev.on_clicked(prevNum)
        bprot.on_clicked(rotate)
        bparts.on_clicked(toggleParts)
        buttons = [num_slider,bnext,bprev,bprot,bparts]
        # buttons must be returned so that they dont get garbage collected
        return fig,ax,buttons