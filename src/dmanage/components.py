# -*- coding: utf-8 -*-
import os
import tables as tb
import pandas as pd
import copy
import gc

class SoftCache(dict):
    def __getattr__(self, key):
        if not key in self.keys():
            raise AttributeError("No '%s' in cache"%(key))
        return self[key]
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def __getitem__(self, key : str):
       if (not key in self.keys() and key[0] != '_'):
           raise KeyError("No '%s' in cache"%(key))
       return super().__getitem__(key)
   
    def __setitem__(self, key : str, value : all):
       return super().__setitem__(key, value)
        
    def get(self,key,method=None,*args,**kwargs):
        if (not key in self.keys()) and (method is not None):
            self[key] = method(*args, **kwargs)
        return self[key]
    
    
class HardCache():
    def __init__(self,loc='./processed/',name='cache.h5'):
        self.loc = loc
        self.name = name
        self.path = os.path.join(self.loc,self.name)
        self.h5file = type('Uninitialized', (object,), {'isopen':0})
        
    def open(self):
        """Open the Hard Cache h5 file
        
        This closes all the File objects already open on the Hard cache before 
        opening. This ensures there are no 'lost' File objects. Having an open
        File object may throw errors because 'it is already open'. Sometimes 
        re-opening an open File object will work in Python, sometimes not. Also,
        Other programs might not be able to open open File objects.
        """
        self.close()
        if not self.h5file.isopen:
            if os.path.exists(self.path):
                self.h5file = tb.open_file(self.path, mode="a")
            else:
                self.h5file = tb.open_file(self.path, mode="w",title='Hard Cache')
            
    def close(self):
        """close the h5 file
        
        This closes the h5 file if it has the File object. Sometimes if not closed
        properly and reopened, the FileRegistry has multiple instances of the File object. 
        The h5 file will appear closed and the object is 'lost'. If that is
        the case, this function searches the open h5 files in the FileRegistry,
        grabs the File object, and closes it.
        """
        openFiles = tb.file._open_files.get_handlers_by_name(self.path)
        if self.h5file.isopen:
            self.h5file.close()
        elif len(openFiles)>0:
            for openFile in copy.copy(openFiles):
                openFile.close()
            self.h5file = openFile
        
             
        
    def close_all(self):
        """This closes all open h5 files
        
        Other programs, such as hdfView, wont open h5 files that are already open. 
        If an error occurs while the h5 file is open, other programs can't open it. 
        This class will check if the file is still open before opening it, so no
        problem there. If external programs cant open the file, call this or
        restart the kernel. However, The behavior is a bit unexpected and some
        of the errors I saw before dont happen every time. so debug when they
        happen. 
        """
        tb.file._open_files.close_all()
        # old school method
        # for obj in gc.get_objects():   # Browse through ALL objects
        #     if isinstance(obj, tb.file.File):   # Just HDF5 files
        #         try:
        #             obj.close()
        #         except:
        #             pass # Was already closed
        
        
    def keys(self):
        """Gets the keys of the availiable data
        
        This walks through the groups and checks for leaves. Leaves are
        hanging nodes with no children; in other words, it's actual data.
        There could be a better way to do this, but I'm an amateur.
        
        Right now There are only DataFrames that can be stored in the 
        '/DataFrames' group. In the future I want to have scalars. And then these
        scalars can be combined with other DataUnits.
        """
        #groups = self.h5file.root._v_children.keys()
        keys = []
        if os.path.exists(self.path):
            self.open()
            for group in self.h5file.walk_groups():
                if bool(group._v_leaves.keys()):
                    keys = keys + [group._v_name]
        return keys
        
    def save(self,data,name):
        # self.open()
        if isinstance(data,pd.core.frame.DataFrame):
            group = '/DataFrames/'+name
            data.to_hdf(self.path,key=group,mode='a',format='table')
        
    def remove(self,name):
        if os.path.exists(self.path): 
            self.open()
            if name in self.keys():
                group = '/DataFrames/'+name
                self.h5file.remove_node(group,recursive=True)
            else:
                raise Warning("No '%s' in Hard Cache, ignoring... Availiable keys: %s"%(name,self.keys()))
        else:
            raise Warning("No Hard Cache created, ignoring...")
    
    def get(self,name):
        
        if name in self.keys():
            self.close()
            group = '/DataFrames/' + name
            df = pd.read_hdf(self.path,group)
        else:
            df = pd.DataFrame()
        return df
    
    
    def delete_all(self):
        if os.path.exists(self.path):
            os.remove(self.path)
    
    def __del__(self):
        self.close()


class Summary():
    """NOT IMPLEMENTED
    """
    def __init__(self,dataPath):
        self.summaryFile = self.baseDir + 'summary.csv'
        self.summaryData = self.read_summary()
    def add_to_summary(self, data, summaryData=None, internalSummary=True):
        
        if summaryData is None:
            summaryData = self.summaryData
        if type(summaryData) is pd.core.frame.Series:
            summaryData = pd.DataFrame(summaryData).T
        if type(summaryData ) is pd.core.frame.DataFrame:
            if summaryData.shape[0] > 1:
                summaryData  = summaryData .T
        if type(data) is dict:
            datas = []
            for key, value in data.items():
                datas = datas + [pd.DataFrame(pd.Series({key:value})).T]
            if len(datas)>0: data = pd.concat(datas,axis=1)
            else: data = pd.DataFrame()
            # data = pd.Series(data)
            # data = pd.DataFrame(data,index=[0],copy=False)
            #data = pd.DataFrame(pd.Series(data)).T
        if type(data) is pd.core.frame.DataFrame:
            if data.shape[0] > 1:
                data = data.T
        if type(data) is pd.core.frame.Series:
            data = pd.DataFrame(data).T
        if not data.empty:
            for indice in data.index:
                if type(data.loc[indice]) is pd.core.frame.DataFrame:
                    if not type(data.loc[indice].index) is pd.core.indexes.range.RangeIndex:
                        data[indice] = data.loc[indice].reset_index()
            summaryData = pd.concat([summaryData.reset_index(drop=True),data.reset_index(drop=True)],axis=1,ignore_index=False)
            summaryData = summaryData.loc[:,~summaryData.columns.duplicated(keep='last')]
            if internalSummary:
                self.summaryData = summaryData
        return summaryData
    
    
    def save_summary(self, saveType ='csv'):
        #### put all DataFrame data at the end
        self.summaryData = self.summaryData[self.summaryData.dtypes.sort_values().index]
        
        if saveType == 'excel':
            self.summaryData.to_excel(self.summaryFile)
        else:
            self.summaryData.to_csv(self.summaryFile) 
        
    def read_summary(self, ow=False, debug=False):
        if os.path.exists(self.summaryFile) and not ow:
            self.summaryData = pd.read_csv(self.summaryFile)
            self.summaryData = self.summaryData.drop(self.summaryData.columns[0],axis=1)
        else:
            # self.summaryData = pd.Series()
            self.summaryData = pd.DataFrame()
            
        #### check for DataFrame Strings (NOT NEEDED ??????)
        for col in self.summaryData.columns:
            # float(self.summaryData.loc[col][0])
            if type(self.summaryData[col][0]) is str:
                #### attempt to make it a DataFrame
                if '\n' in self.summaryData[col][0]:
                    try: 
                        value = pd.read_csv(io.StringIO(self.summaryData[col][0]),delim_whitespace=True)
                        #value = value.set_index(value.columns[0])
                        self.summaryData[col].loc[0] = value
                    except:
                        if debug:
                            print('Unable to Coerce %s  to Dataframe'%(col))
        return self.summaryData



if __name__ == "__main__":
    pass



