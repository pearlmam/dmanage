#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 16 19:42:59 2021

This Opens H5 files
@author: marcus
"""
import collections
import numpy as np              # array functions and manipulation 
import numpy.matlib
# import h5py                     # H5 file package
import tables
import glob                     # searching files function
import os                       # filename manipulation
import pandas as pd
from multiprocess import Pool
import time
import natsort
import copy
from dmanage.plugins.vsim.loader import VsHdf5
from dmanage import dfmethods as dfm
from dmanage.utils.utils import child_override

from dmanage.dfmethods.convert import numpy2DF,createBounds
from dmanage.methods.functions import checkExist,vrrotvec

class UniMesh():
    """
    Reads the information from the VSim universe file to get information about the mesh
    """
    def __init__(self, folder,file=None):
        fileExists = os.path.exists(str(file))
        if file is None or not fileExists:
            self.uniFile = glob.glob(folder + '/*_Globals_*')
            if len(self.uniFile) < 1:
                raise Exception("No Universe H5 file found, Not a VSim Directory: '%s'"%folder)
            else:
                self.file = self.uniFile[0]
        else:
            self.file = file
        self.fileSuffix = (os.path.basename(self.file)).split('_')[-2]
        self.M = VsHdf5.Mesh(fileName=self.file)
        self.UB = self.M.getUpperBounds()
        self.LB = self.M.getLowerBounds()
        self.NC = self.M.getNumCells()
        self.dim = len(self.NC)
        self.kind = self.M.getKind()
        self.axes = self._getAxes()
        self.d = (self.UB-self.LB)/self.NC

    
    
    def getMesh(self):
        bounds = self.getBounds()
        if len(bounds) == 3: mesh = np.meshgrid(bounds[0],bounds[1],bounds[2])[0]
        elif len(bounds) == 3: mesh = np.meshgrid(bounds[0],bounds[1])[0]
        elif len(bounds) == 3: mesh = np.meshgrid(bounds[0])[0]
        return mesh
        
    def getBounds(self):
        bounds = []
        if (self.kind == 'uniform') or (self.kind == 'Cartesian'):
            for i in range(len(self.NC)): 
                bounds = bounds + [np.linspace(self.LB[i], self.UB[i], self.NC[i]+1)]
        elif self.kind == 'rectilinear':
                bounds = bounds + [self.M.axis0.dataset]
                if len(self.M.axis1.dataset) != 0:
                    bounds = bounds + [self.M.axis1.dataset]
                if len(self.M.axis2.dataset) != 0:
                    bounds = bounds + [self.M.axis2.dataset]
        else:
            raise Exception('getBounds() is not implemented for vsKind=%s'%self.kind)
        return bounds
    
    def getBoundsDict(self):
        bounds = self.getBounds()
        boundsDict = {}
        for i,axis in enumerate(self.axes):
            boundsDict[axis] = bounds[i]
        return boundsDict
    
    def _getAxes(self):
        h5 = tables.open_file(self.file)
        nodeName = '/'+ self.fileSuffix
        if nodeName[1:] in h5.get_node('/')._v_children.keys():
            node = h5.get_node(nodeName)
            attrs = node.attrs._v_attrnames
        else:
            node = None
            attrs = []
        if 'vsAxisLabels' in attrs:
            axes = node.attrs.vsAxisLabels.decode('ascii').split(',')
        else:
            ##### old version doesnt have labels, add them here but it might be 2D
            if self.dim == 3: axes = ['X','Y','Z']
            elif self.dim == 2: axes = ['X','Y']
            elif self.dim == 1: axes = ['X']
        axes = [a.lower() for a in axes]
        h5.close()
        return axes
    
class GeoData():
    def __init__(self, folder,geoFiles):
        self.files = geoFiles
        self.UNI = UniMesh(folder,file=geoFiles[0])
        self.types = [file.split('_')[-2] for file in geoFiles]
    
    @child_override
    def readAsDF(self,geoType):
        array,bounds = self.readAsNumpy(geoType)
        DF = numpy2DF(array, bounds,colName=geoType)
        return DF
        
    def readAsNumpy(self, geoType):
        # negative values are metal and positive are within the simulation domain
        i = self.types.index(geoType)
        file = self.files[i]
        h5 = tables.open_file(file)
        array = h5.get_node('/'+geoType).read()            # the array has a fourth dimension
        bounds = self.UNI.getBoundsDict()        # bounds incomplete if 4th dim is kept
        # bounds['labels'] = ['node','center']   # add the fourth dimension
        # array = array[:,:,:,0]                   # 4th dim is removed by selecting center
        array = np.take(array,indices=0,axis=-1)   # remove last dim
        h5.close()
        return array,bounds

    
class H5Hist():
    """
    History component for VSim data
    """
    def __init__(self, folder, fileName = None,uniFile=None):
        if fileName is None:
            self.histFile = glob.glob(folder + '/*_History.h5')[0]
        else:
            self.histFile = os.path.join(folder, '') + fileName
        self.H = VsHdf5.Mesh(fileName=self.histFile)

        h5 = tables.open_file(self.histFile)
        self.types = list(h5.root._v_children.keys())
        self.types.remove('runInfo')
        for theType in copy.deepcopy(self.types):
            if 'timeSeries' in theType:
                self.types.remove(theType)
        self.tend,self.TSTEPS,self.dt = self._readTimeInfo(h5)
        self.UNI = UniMesh(folder,file=uniFile)
        self.folder = folder
        h5.close()
        return
    
    @child_override
    def readSeriesAsDF(self, baseName,concat=True,axis=1):
        # want to include this in self.readAsDF
        histNames = [ hist for hist in self.types if baseName in hist]
        histNames = natsort.natsorted(histNames)
        DFs = self.readAsDF(histNames,concat=False,axis=axis)
        if concat:
            if axis == 0:
                for histName,DF in zip(histNames,DFs):
                    DF.rename(columns={histName:baseName},inplace=True)
            DFs = pd.concat(DFs,axis=axis,verify_integrity=False)
            DFs = DFs.loc[:,~DFs.columns.duplicated()].copy()
        return DFs,histNames
    
    @child_override
    def readAsDF(self,histNames,concat=True,axis=1,**kwargs):
        if not type(histNames) is list: histNames = [histNames]
        DFs = []
        for histName in histNames:
            DFs = DFs + [self._readAsDF(histName,**kwargs)]
        if concat and DFs:
            DFs = pd.concat(DFs,axis=axis,verify_integrity=False)
            DFs = DFs.loc[:,~DFs.columns.duplicated()].copy()
        elif not DFs:
            DFs = pd.DataFrame([])
        return DFs
 
    def _readAsDF(self, histName,**kwargs):
        if type(histName) is list: 
            histName = histName[0]
        
        if checkExist(histName,self.types,output=False):
            h5 = tables.open_file(self.histFile)
            node = h5.get_node('/'+ histName) 
            attrs = node._v_attrs._v_attrnames
            array = node.read()
            s = array.shape
            TSTEPS = array.shape[0]
            # dt = self.tend/TSTEPS
            
            if not (self.dt is None):
                # this is VSim Version <=12.2, need to calculate t
                # need to figure out the dump rate to determine the actual end time
                dumpRate = np.ceil(self.TSTEPS/TSTEPS)
                DTSTEPS = round((self.TSTEPS/dumpRate%1)*dumpRate)
                
                # now generate the time series with the actual tend
                t0 = 0.0
                t1 = self.tend-(DTSTEPS*self.dt)
            
                for kwarg in kwargs:
                    if kwarg == 't0': t0 = kwargs[kwarg] 
                    elif kwarg == 't1': t1 = kwargs[kwarg]
                
                t = np.linspace(t0,t1,TSTEPS)
            else:
                timeSeries = '/timeSeries' + histName
                timeNode = h5.get_node(timeSeries)
                t = timeNode.time.read()
            
            
            
            if len(s) == 3 or len(s) == 4:
                # with length == 4, this is a curveSemiCircle history
                # with length == 3, this is field on line or a tagged particle history
                
                attrNames = node._v_attrs._v_attrnames
                # trajectory has ['vsMesh', 'vsType']
                # fieldOnLine has ['vsMesh', 'vsType', x, y, z]
                # semiCircle has ['CurveSemiCircle','vsMesh', 'vsType', x, y, z]
                
                if len(attrNames) < 3: 
                    histType = 'taggedParticle'
                    iNames = ['t','tag','data']
                    colName = [histName]
                    ###### need to infer dataColumns... sad
                    # dataNames = ['x','y','z','ux','uy','uz']
                
                    dataNames = self.UNI.axes + ['u' + axisName for axisName in self.UNI.axes]
                    bounds = createBounds(array,iNames,bounds = {'t':t,'data':dataNames})
                    DF = numpy2DF(array,bounds,colName,inplace=True)
                    #DF = DF['trajectory'].unstack(level='data') # to unstack that data to a list format
                    
                    # this gets rid of zero values where the particle doesnt exist
                    # DF.columns.name = 'hists'
                    # DF = DF.unstack().reorder_levels(['data','hists'],axis=1)
                    # DF = DF.loc[DF[self.UNI.axes].ne(0).all(axis=1)]
                    # DF = DF.reorder_levels(['hists','data'],axis=1).stack()
                else:
                    # this is field on line or a tagged particle history
                    if len(s) == 4: histType = 'semiCircle'
                    elif len(s) == 3: histType = 'fieldOnLine'
                    
                    if histType == 'semiCircle': array = np.reshape(array,(s[0], s[1],s[3]) )
                    # convert from 3D array to pandas dataframe
                    iNames = ['t','point','v']
                    colName = histName
                    bounds = createBounds(array,iNames,bounds = {'t':t})
                    DF = numpy2DF(array,bounds,colName,inplace=True)
    
                    # add position columns
                    for i,label in enumerate(self.UNI.axes):
                        colName = label
                        bounds = self.UNI.getBounds()
                        if histType == 'fieldOnLine': pos = bounds[i][node.get_attr(label)]
                        else: pos = node.get_attr(label)
                        vecLength = array.shape[2]
                        pos = np.tile(np.repeat(pos,vecLength),TSTEPS)  
                        DF.insert(i,colName, pos)
                    # the following line lowers the mem usage but there are 'redundant' indices
                    #DF = DF.set_index(['x','y','z'],append=True).reorder_levels(['t','point','x','y','z','v'])
                    if histType == 'semiCircle':
                        # this is a curveSemiCircle
                        ##### old way to get x, y, z. old school
                        normal = node.get_attr('CurveSemiCircle')[5:]
                        zhat = np.array([0,0,1])
                        r = vrrotvec(zhat,normal)
                        xp = np.matmul(r,np.array([1, 0, 0]))
                        yp = np.matmul(r,np.array([0, 1, 0]))
                        x = np.matmul(DF[self.UNI.axes].to_numpy(),xp)
                        y = np.matmul(DF[self.UNI.axes].to_numpy(),yp)
                        
                        phi = np.arctan2(y,x)
                        r = np.sqrt(x**2 + y**2)
                        #phi = np.repeat(phi,TSTEPS)
                        DF.insert(3,'phi',phi)
                        DF.insert(4,'r',r)
                        #DF = DF.set_index(['phi'],append=True).reorder_levels(['t','point','x','y','z','phi','v'])
            elif len(s) == 2:
                # this could be a absorber data or a average vector history
                if 'ptclDataDescription' in attrs:
                    cols = node.get_attr('ptclDataDescription').decode('ascii').replace("'","").replace(" ","").split(',')
                    DF = pd.DataFrame(array,columns=cols).set_index('tag').sort_index()
                    DF.columns.name = 'data'
                elif 'fieldComponents' in attrs:
                    cols = list(node.get_attr('fieldComponents'))
                    DF = pd.DataFrame(array,columns=cols,index=t)
                    DF.index.name = 't'
                    DF.columns.name = 'v'
                
                DF = DF.stack()
                DF.name = histName
                DF = DF.to_frame()
            elif len(s) == 1:          # it's a scaler History
                DF = numpy2DF(array,{'t':t},histName,inplace=True)
            else: raise Exception('This history has no method to read yet')
            h5.close()
        else:
            print('%s is not a dataset'% (histName))
            DF = None
        return DF
    
    def readAsNumpy(self, histName):
        if checkExist(histName,self.types,output=False):
            h5 = tables.open_file(self.histFile)
            node = h5.get_node('/'+ histName) 
            attrs = node._v_attrs._v_attrnames
            array = node.read()
            s = array.shape
            TSTEPS = array.shape[0]

            t = np.linspace(0.0,self.tend,TSTEPS)
            
            if len(s) == 3 or len(s) == 4:
                if s[2] == 6: 
                    dataNames = ['x','y','z','ux','uy','uz']
                    bounds = {'t':t,'tag':np.arange(0,s[1]),'data':dataNames}
                else: 
                    if len(s) == 4: array = np.reshape(array,(s[0], s[1],s[3]) )
    
                    # convert from 3D array to pandas dataframe
                    bounds = {'t':t,'point':np.arange(0,s[1]),'v':np.arange(0,s[1])}
                    
                    poss = np.zeros([s[1],len(self.UNI.axes)])
                    # add position columns
                    for i,label in enumerate(self.UNI.axes):
                        if len(s) == 3: pos = node.get_attr(label)*self.UNI.d[i] + self.UNI.LB[i]
                        else: pos = node.get_attr(label)
                        bounds['extras'] = {label:np.array(pos)}
                        #bounds[label] = np.array(pos)
                        poss[:,i] = pos
                        
                    if len(s) == 4:
                        # determine the angle phi of the CurveSemiCircle history
                        normal = node.get_attr('CurveSemiCircle')[5:]
                        zhat = np.array([0,0,1])
                        r = vrrotvec(zhat,normal)
                        xp = np.matmul(r,np.array([1, 0, 0]))
                        yp = np.matmul(r,np.array([0, 1, 0]))
                        x = np.matmul(poss,xp)
                        y = np.matmul(poss,yp)
                        phi = np.arctan2(y,x)
                        bounds = self.replaceBounds(bounds,'point','phi',vals=phi)
                        #bounds['phi'] = phi
            elif len(s) == 2:
                raise Exception('This history has no method to read yet')
            elif len(s) == 1:          # it's a scaler History
                bounds = {'t':t}
            h5.close()     
        else:
            print('%s is not a dataset'% (histName))
            array = None
            bounds = None
        return array,bounds
    
    def checkDataset(self,histNames,output=False):
        if not type(histNames) is list: histNames = [histNames]
        h5 = tables.open_file(self.histFile)
        check = True
        histNamesOut = []
        for histName in histNames:
            if checkExist(histName,self.types,output=False):
                node = h5.get_node('/'+histName)
                s = node.shape
                if len(s) == 0:
                    print('%s is not a dataset'% (histName))
                    check = False
                else:
                    histNamesOut = histNamesOut + [histName]
            else:
                check = False
        h5.close()
        return check,histNamesOut
    
    ###########################################
    #       private methods
    ###########################################
    def _readTimeInfo(self,h5):
        if 'timeSeries' in h5.root._v_children.keys():
            node = h5.get_node('/timeSeries')
            attrs = node._v_attrs._v_attrnames
            if 'time' in node._v_children.keys():
                t = np.array(node.time.read())
                self.tend = t[-1]
                self.TSTEPS = t.shape[0]
                self.dt = self.tend/self.TSTEPS
            else:
                ##### this is for version VSim 7.2
                self.tend = node._v_attrs.vsUpperBounds[0]
                self.TSTEPS = node._v_attrs.vsNumCells[0]
                self.dt = self.tend/self.TSTEPS
        else: 
            # version VSim 12.3 doesnt have generic /timeSeries anymore
            # This steps through each history to check for max time
            # if the dumprate is not every timestep, then the tend might be wrong
            # one of the histories must have dumped at the last timestep to be correct
            tend = 0.0
            for key in h5.root._v_children.keys():
                if 'timeSeries' in  key:
                    node = h5.get_node('/' + key)
                    tend = max(tend,max(node.time.read()))
            self.tend = tend
            self.TSTEPS = None
            self.dt = None
        
        return self.tend,self.TSTEPS,self.dt
    
    

class H5Particles():
    def __init__(self, folder,partTypes=None,uniFile=None):
        self.types = partTypes
        self.files = {}
        self.steps = {}
        self.stepNums = {}
        self.info = {}
        self.UNI = UniMesh(folder,file=uniFile)
        for partType in partTypes:
            self.files[partType] = glob.glob(folder + '/*_' + partType + '_*')
            self.files[partType] = sorted(self.files[partType],key=lambda x: int(os.path.splitext(x)[0].split('_')[-1]))
            self.steps[partType] = len(self.files[partType])
            nums = []
            for files in self.files[partType]:
                basename = os.path.basename(files)
                basename = os.path.splitext(basename)[0]
                nums = nums + [int(basename.split('_')[-1])]
            self.stepNums[partType] = nums
            self.info[partType] = self._getPartInfo(partType)
    
    @child_override
    def readAsDF(self,steps=None,partType=None,relData=None,relTags=None,sampleRatio=False,nc=1):
        if partType is None:
            raise Exception("partType must be defined as one of %s"%self.types)
            
        startTime = time.time()
        print('  Reading particle dumps with %i cores...'%(nc), end=' ')
        
        if steps is None or type(steps) is str: steps = range(0,self.steps[partType])
        readAsDF_ = dfm.wrapper.parallelize_iterator_method(self._readAsDF,concat=True)
        DF = readAsDF_(steps,partType=partType,relData=relData,relTags=relTags,sampleRatio=sampleRatio,nc=nc)
        
        executionTime = (time.time()-startTime)
        print(' Done in %0.2f seconds'%(executionTime))
        
        return DF
    
    
    def _readAsDF(self,step,partType,relData=None,relTags=None,sampleRatio=False,nc=1):
        """
        
        """
        if step > self.steps[partType]:
            raise Exception("Particle '%s' only has %d steps and step %d is out of range"%(partType,self.steps[partType],step))
        
        h5 = tables.open_file(self.files[partType][step])
        
        colNames = self._getColumnNames(h5)
        if 'tags' in colNames: colNames[colNames.index('tags')] = 'tag'
        node = h5.get_node('/'+partType)
        array = node.read()
        t = node._v_attrs.time
        DF = pd.DataFrame(array,columns=colNames)
        
        DF.index.name = 'num'
        DF.insert(0,'t',t)
        DF.set_index('t',append=True,inplace=True)
        DF = DF.reorder_levels(['t','num'])
        if 'weight' in colNames: 
            DF['weight'] = DF['weight']*self.info[partType]['ppm'] 
        else: 
            DF['weight'] = self.info[partType]['ppm']
        
        if type(relData) != type(None):
            DF = DF[relData]
        if issubclass(type(DF), pd.core.series.Series): 
            DF = DF.to_frame()
        
        if ('tag' in DF.columns) and (len(DF.columns) != 1): 
            DF = DF.groupby(['tag','t']).first().sort_index()
        # this is very slow
        if type(relTags) != type(None):
            iTags = list(DF.index.get_level_values('tag'))
            matchTags = []
            for iTag in iTags:
                if iTag in relTags:
                    matchTags = matchTags + [iTag]
            DF = DF.loc[matchTags]
            
        if sampleRatio != 0: DF = DF.sample(int(len(DF)*sampleRatio),axis=0).sort_index()
        h5.close()
        return DF 
    
    def array2DF(self,array,t,colNames,partType):      
        DF = pd.DataFrame(array,columns=colNames)
        DF.index.name = 'num'
        DF.insert(0,'t',t)
        if ('tag' in DF.columns) and (len(DF.columns) != 1): 
            DF = DF.set_index(['tag','t'],drop=True).sort_index()
        else:
            DF.set_index('t',append=True,inplace=True)
        # DF = DF.reorder_levels(['t','num'])
        if 'weight' in colNames: 
            DF['weight'] = DF['weight']*self.info[partType]['ppm'] 
        else: 
            DF['weight'] = self.info[partType]['ppm']
        return DF

    def readAsNumpy(self,partType,step):
        h5 = tables.open_file(self.files[partType][step])
        node = h5.get_node('/'+partType)
        array = node.read()
        t = node._v_attrs.time
        dataNames = self._getColumnNames(h5)
        iNames = ['num','data']
        bounds = createBounds(array,iNames,bounds={'data':dataNames})
        bounds['t'] = t
        h5.close()
        return array,bounds
    
    ##########################
    #   private methods
    ##########################
    
    def _getColumnNames(self,h5):
        keys = list(h5.root._v_children.keys())
        remKeys = ['globalGridGlobalLimits', 'runInfo', 'time']
        for remKey in remKeys:
            if remKey in keys:
                keys.remove(remKey)
                
        partType = keys[0]
        colNames = h5.get_node('/'+partType).get_attr('vsLabels').decode('ascii').split(',')
        colNames = [colName.split('_')[-1] for colName in colNames]
        return colNames
    
    def _getPartInfo(self,partType):
        i = 0
        tFirstFound = False
        while (i < self.steps[partType]) and not tFirstFound:
            h5 = tables.open_file(self.files[partType][i])
            node = h5.get_node('/'+partType)
            if node.shape[0] > 0:
                tFirstFound = True
            else:
                h5.close()
                i += 1
                
        #node = h5.get_node('/'+partType)
        info = {}
        info['mass'] = node.get_attr('mass')
        info['charge'] = node.get_attr('charge')
        info['ppm'] = node.get_attr('numPtclsInMacro')
        info['tFirst'] = node.get_attr('time')
        h5.close()
        
        h5 = tables.open_file(self.files[partType][-1])
        node = h5.get_node('/'+partType)
        info['tLast'] = node.get_attr('time')
        h5.close()
        return info
    
    
    ##########################
    #   Possibly OBSOLETE CODE BELOW
    ##########################
    
    def getUnique(self,partType,steps=None,col='tag',nc=1):
        if steps is None or type(steps) is str: steps = range(0,self.steps[partType])
        if not isinstance(steps,collections.abc.Iterable): steps = [steps]
        nc = min(nc,len(steps))
        
        if nc>1:
            if type(steps) is range: steps=np.array(steps)
            stepss = np.array_split(np.array(steps),nc)
            variables = [(partType,steps,col,1) for steps in stepss]
            pool = Pool(processes=nc)
            F =  pool.starmap_async(self.getUnique,variables)
            
            arraylist = F.get()
            pool.close()
            array = np.unique(np.concatenate(arraylist))
        else:
            # DF = dm.PerfectDataFrame()
            arrayList = []
            for step in steps:
                arrayList = arrayList + [ self._getUnique(partType,step,col) ]

            array = np.unique(np.concatenate(arrayList))

        return array
    
    def _getUnique(self,partType,step,col='tag'):
        # if not type(col) is list: col = [col]
        DF = self._readAsDF(partType,steps=step,relData=col)
        if col in DF.columns:
            if not issubclass(type(DF), pd.core.series.Series): 
                DF = DF[col].unique()
            else:
                DF = DF.unique()
        else:
            print("'%s' is not a column in the %s dump data"%(col,partType))
        return DF
    
    
    
    ##########################
    #   OBSOLETE CODE BELOW
    ##########################
    def ___getMaxMinStep(self,partType,step,coords='cyl',phiRange='2pi'):
        DF = self.readAsDF(partType,step)
        if not DF.empty:
            if coords == 'cyl':
                DF = self.cart2Cyl(DF,phiRange=phiRange)
            DF = DF.agg(['min','max'])
        else: 
            DF=None
        return DF
    
    def ___getMaxMinSteps(self,partTypes,steps=None,coords='cyl',phiRange='2pi',nc=1):
        """
        Gets max and min of all dumps of the columns in the particle steps
        """
        if steps is None: steps = range(0,self.steps[partTypes[0]])
        
        if not type(partTypes) is list:
            partTypes = [partTypes]
        else:
            # check if same number of steps
            stepsCheck = [self.steps[partType] ==  self.steps[partTypes[0]] for partType in partTypes] 
            if not stepsCheck: raise Exception("For partTypes = %s, the number of steps are not equal!"%partTypes)
        
        DFlist = []
        for partType in partTypes:
            if nc > 1:
                theArgs = [(partType,i,coords,phiRange) for i in steps]
                pool = Pool(processes=nc)
                F =  pool.starmap_async(self.getMaxMinStep,theArgs)
                DFlist = DFlist + F.get()
                pool.close()
                
            else:
                for step in steps:
                    DF = self.getMaxMinStep(partType=partType,step=step,coords=coords,phiRange=phiRange)
                    DFlist = DFlist + [DF]
         
            DF = pd.concat(DFlist,axis=1).transpose()
            G = DF.groupby(DF.index)
            DF = pd.concat([G['max'].max().reindex(DF.index.unique()),G['min'].min().reindex(DF.index.unique())],axis=1)    
          
        return DF.transpose()
    
    
    
    def ___readAllAsNumpy(self,partType,steps=None):
        # UNAVAILABLE because it is non-uniform array in time
        pass
     
    def ___readAsDF(self,partType,steps=None,relData=None,tagRatio=None,nc=1):
        startTime = time.time()
        relTags = None
        
        if type(tagRatio) != type(None):
            
            print('  Getting unique tags for decimation...', end=' ')
            relTags = self.getUnique(partType,steps=steps,col='tag',nc=nc)
            relTags = np.random.choice(relTags,int(len(relTags)*tagRatio),replace=False)
            relTags.sort()
            print(' Done')
        print('  Reading particle dumps with %i cores...'%(nc), end=' ')
        DF = self._readAsDF(partType,steps,relData,relTags,nc)
        executionTime = (time.time()-startTime)
        print(' Done in %0.2f seconds'%(executionTime))
        return DF
        
class H5Fields():
    """
    This class gets info about the set of vector? fields
    """
    def __init__(self, folder, fieldTypes = ['E']):
        if not type(fieldTypes) is list: fieldTypes = [fieldTypes]
        self.types = fieldTypes
        self.files = {}
        self.steps = {}
        self.stepNums = {}
        
        for fieldType in fieldTypes:
            self.files[fieldType] = glob.glob(folder + '/*_' + fieldType + '_*')
            self.files[fieldType] = sorted(self.files[fieldType],key=lambda x: int(os.path.splitext(x)[0].split('_')[-1]))
            self.steps[fieldType] = len(self.files[fieldType])
            nums = []
            for file in self.files[fieldType]:
                basename = os.path.basename(file)
                basename = os.path.splitext(basename)[0]
                nums = nums + [int(basename.split('_')[-1])]
            self.stepNums[fieldType] = nums
        if len(fieldTypes)>0: uniFile = self.files[fieldType][0]
        else: uniFile=None
        self.UNI = UniMesh(folder,file=uniFile)
        
    @child_override
    def readAllAsDF(self,fieldType,steps=None,nc=1):
        array,bounds = self.readAllAsNumpy(fieldType,steps,nc)
        DF = numpy2DF(array, bounds)
        return DF
    
    @child_override
    def readAsDF(self, fieldType,step):
        h5 = tables.open_file(self.files[fieldType][step])
        vcolName = 'v'
        node = h5.get_node('/'+fieldType)
        array = node.read()
        t = node._v_attrs.time
        bounds = self.UNI.getBoundsDict()
        iNames = self.UNI.axes + [vcolName]
        colName = fieldType
        bounds = createBounds(array,iNames,bounds = bounds)
        DF = numpy2DF(array,bounds,colName,inplace=True)

        DF.insert(0,'t',t)
        DF.set_index('t',append=True,inplace=True)
        DF = DF.reorder_levels(['t','x','y','z','v'])
        return DF
    @child_override
    def readAllAsNumpy(self,fieldType,steps=None,nc=1):
        if type(steps) == type(None) or steps == 'all': steps = range(0,self.steps[fieldType])
        
        
        array,bounds = self.readAsNumpy(fieldType,steps[0])
        s = len(array.shape)
        array = np.expand_dims(array,axis=s)
        if nc>1:
            theArgs = [(fieldType,i) for i in steps[1:]]
            if len(theArgs)>0:
                pool = Pool(processes=nc)
                F =  pool.starmap_async(self.readAsNumpy,theArgs)
                #(arrayList,boundsList) = F.get()
                tupleList = F.get()
                arrayList,boundsList = list(zip(*tupleList))
                arrayList = [array] + [np.expand_dims(array,axis=s) for array in arrayList]
                boundsList = [bounds] + list(boundsList)
                pool.close()
                array = np.concatenate(arrayList,axis=s)
                bounds['t'] = np.array([bounds['t'] for bounds in boundsList])
            else:
                bounds['t'] = [bounds['t']]
                bounds['t'] = np.array(bounds['t'])
        else:
            bounds['t'] = [bounds['t']]
            for step in steps[1:]:
                tempArray,tempBounds = self.readAsNumpy(fieldType,step)
                tempArray = np.expand_dims(tempArray,axis=s)
                array = np.concatenate([array,tempArray],axis=s)
                bounds['t'] = bounds['t'] + [tempBounds['t']]
            bounds['t'] = np.array(bounds['t'])
        return array,bounds
    @child_override
    def readAsNumpy(self, fieldType, step):
        h5 = tables.open_file(self.files[fieldType][step])
        vcolName = 'v'
        node = h5.get_node('/'+fieldType)
        array = node.read()
        t = node._v_attrs.time
        bounds = self.UNI.getBoundsDict()
        bounds[vcolName] = [i for i in range(array.shape[-1])]
        bounds['t'] = t
        return array,bounds
    
    def ___readAllAsDF(self,fieldType,steps=None):
        # slower than reading as numpy
        if type(steps) == type(None): steps = self.steps[fieldType]
        DF = pd.DataFrame()
        for step in range(steps):
            DF = pd.concat([DF,self.readAsDF(fieldType,step)])
        return DF
        
class InputVariables():
    def __init__(self,varFile):
        self.varFile = varFile
        self.preName = os.path.basename(varFile).replace('Vars.py','')
        
    @child_override
    def read(self, varList,warn=False):
        """
        extracts variables in varList from the Vars.py file. Only the last variable 
        declaration in Vars.py is used. returns dictionary elemnts {"varname":value,...}
        """
        if type(varList) is not list:
            varList = [varList]
        varList_copy = list(varList)
        source = open(self.varFile, 'r')
        variables = {}
        if 'date' in varList_copy: 
            variables['date']=self.getDate()
            varList_copy.remove('date')
            
        for line in reversed(list(source)):
            # print(line)
            i = 0
            for item in varList_copy:
                if item == line.split('=')[0].strip():
                    try: variables[item]=float(line.strip().split('=')[1])
                    except: variables[item]=line.strip().split('=')[1]
                    varList_copy.pop(i)
                i+=1
        source.close()
        if warn:
            print('Variables Not Found: %s'%varList_copy)
        return variables
    
    def getDate(self):
        source = open(self.varFile, 'r')
        for line in list(source):
            if '### Translation: ' in line:
                date = line.rstrip().replace('### Translation: ','')
        return date

class VSim():
    def __init__(self,folder):

        if not self.isValid(folder):
            print('Not a valid VSim folder')
            
        else:
            self.sim = 'VSim'
            self.PreVars = InputVariables(self.varFile)
            self.Hists, self.Parts,self.Fields,self.Geos = self.loadComponents(folder)
            self.components = ['Hist','Parts','Fields','Geos','PreVars']
   
    def isValid(self,folder):
        folder = os.path.join(folder,'')
        varFile = glob.glob(folder + '/*Vars.py')
        if len(varFile) == 0:
            # print(folder + ' is not a VSim data directory!')
            valid = False
        else:
            self.varFile = varFile[0]
            valid=True
        return valid
    
    def loadComponents(self,folder):
        ignores = ['Globals', 'universe','History']
        files = np.array(glob.glob(folder + '/*.h5'))
        types = []
        for file in files:
            if 'History' in file:
                histExist = True
                types = types + ['History']
            else:  
                types = types + [file.split('_')[-2]] 
        
        types,i = np.unique(types,return_index=True)
        files = files[i]
        fieldTypes = []; particleTypes = []; geoTypes = []; geoFiles = []
        for i,file in enumerate(files):
            if not any([ignore in file for ignore in ignores ]):
                try: 
                    h5 = tables.open_file(file)
                    rootNodes = h5.get_node('/')._v_children.keys()
                    if 'poly' in rootNodes: 
                        geoFiles = geoFiles + [str(file)] # its a geometry
                    elif not 'globalGridGlobalLimits' in rootNodes: 
                        pass # its a multifield
                    elif 'globalGridGlobal' in rootNodes: 
                        fieldTypes = fieldTypes + [str(types[i])] # its a field
                    else: 
                        particleTypes = particleTypes + [str(types[i])]
                    h5.close()
                except:
                    #os.path.basename(file)
                    print("Cannot open '%s', it my be corrupt, this file should be deleted"%os.path.basename(file))
        if histExist:
            Hists = H5Hist(folder,uniFile=geoFiles[0])
        
        Geos = GeoData(folder,geoFiles)
        Parts = H5Particles(folder,particleTypes,uniFile=geoFiles[0])
        Fields = H5Fields(folder,fieldTypes)
        return Hists,Parts,Fields,Geos
        
    def _loadComponents(self,folder,DDobj=None):
        DDobj.PreVars = InputVariables(self.varFile) # ???
        ignores = ['Globals', 'universe','History']
        files = np.array(glob.glob(folder + '/*.h5'))
        types = []
        for file in files:
            if 'History' in file:
                histExist = True
                types = types + ['History']
            else:  
                types = types + [file.split('_')[-2]] 
        
        types,i = np.unique(types,return_index=True)
        files = files[i]
        fieldTypes = []; particleTypes = []; geoTypes = []; geoFiles = []
        for i,file in enumerate(files):
            if not any([ignore in file for ignore in ignores ]):
                try: 
                    h5 = tables.open_file(file)
                    rootNodes = h5.get_node('/')._v_children.keys()
                    if 'poly' in rootNodes: 
                        geoFiles = geoFiles + [str(file)] # its a geometry
                    elif not 'globalGridGlobalLimits' in rootNodes: 
                        pass # its a multifield
                    elif 'globalGridGlobal' in rootNodes: 
                        fieldTypes = fieldTypes + [str(types[i])] # its a field
                    else: 
                        particleTypes = particleTypes + [str(types[i])]
                    h5.close()
                except:
                    #os.path.basename(file)
                    print("Cannot open '%s', it my be corrupt, this file should be deleted"%os.path.basename(file))
        
        DDobj.PreVars = InputVariables(self.varFile)
        if histExist:
            DDobj.Hists = H5Hist(folder,uniFile=geoFiles[0])
        
        
        DDobj.Geos = GeoData(folder,geoFiles)
        DDobj.Parts = H5Particles(folder,particleTypes,uniFile=geoFiles[0])
        DDobj.Fields = H5Fields(folder,fieldTypes)
        return None    
    
   
    
if __name__ == "__main__":
    
    
    pass




