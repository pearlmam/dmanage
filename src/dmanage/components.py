# -*- coding: utf-8 -*-
import os
import tables as tb
import pandas as pd
import copy
import io

from dmanage.utils.objinfo import is_iterable

class SoftCache(dict):
    """This is a dict-like component used for storing data
    
    inherited methods:
        self.update()
        self.items()
        self.keys()
        self.pop()
        self.popitem()
        self.values()
        self.clear()
        self.copy()
    
    """
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
        """Gets the value from the cache or the method(args,kwargs)
        Maybe for methods returning tuples, have way to ignore some values using None
        
        """
        iterable = is_iterable(key)
        if not iterable:
            if (not key in self.keys()) and (method is not None):
                self[key] = method(*args, **kwargs)
            return self[key]
        else:
            # # drop None values for the cache check
            # checkKeys = [k for k in key if k is not None]
            
            if not all(x in self.keys() for x in key) and (method is not None):
                # call method and set the tuple result to key iterable
                results = method(*args, **kwargs)
                if type(results) is not tuple:
                    raise Exception("The number of elements in 'key' does not equal the size of the tuple returned by 'method'")
                for k,result in zip(key,results):
                        self[k] = result
            else:
                # get from cache
                results = tuple(self[k] for k in key)
            return results
        
class HardCache():
    """This is a component that stores data in an hdf file on the disk
    
    
    """
    def __init__(self,path='./processed/cache.h5'):
        self.loc = os.path.dirname(path)
        self.path = path
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
    
    def get(self,name,method=None,*args,**kwargs):
        if name in self.keys():
            self.close()
            group = '/DataFrames/' + name
            df = pd.read_hdf(self.path,group)
        elif method is not None:
            df = method(*args, **kwargs)
            self.save(df)
        else:
            raise Exception("No '%s' in keys and method=None, Define method to generate and hard cache the data."%(name))
        return df

    def delete_all(self):
        if os.path.exists(self.path):
            os.remove(self.path)
    
    def __del__(self):
        self.close()


class Summary():
    """This manages summary data in RAM and on the disk
    """
    def __init__(self,path='./processed/summary.csv'):
        self.path = path
        self.loc = os.path.dirname(path)
        self.data = pd.DataFrame()
        self.filetype = path.split('.')[-1]
        
    def add(self, data):
        if type(data) is dict:
            datas = []
            for key, value in data.items():
                datas = datas + [pd.Series(value,name=key)]
            if len(datas)>0: data = pd.concat(datas,axis=1)
            else: data = pd.DataFrame()
        if type(data) is pd.core.frame.DataFrame:
            if data.shape[0] > 1:
                data = data.T
        if type(data) is pd.core.frame.Series:
            data = pd.DataFrame(data).T
        if not data.empty:
            """I dont remember what the follow code is for."""
            # for indice in data.index:
            #     if type(data.loc[indice]) is pd.core.frame.DataFrame:
            #         if not type(data.loc[indice].index) is pd.core.indexes.range.RangeIndex:
            #             data[indice] = data.loc[indice].reset_index()
            self.data = pd.concat([self.data.reset_index(drop=True),data.reset_index(drop=True)],axis=1,ignore_index=False)
            self.data = self.data.loc[:,~self.data.columns.duplicated(keep='last')]
        return self.data
    
    
    def save(self,ow=True):
        filetype = self.filetype
        if not os.path.exists(self.loc):
            os.mkdir(self.loc)
        if not ow:
            data = self.read(warn=False)
            self.data = pd.concat([self.data.reset_index(drop=True),data.reset_index(drop=True)],axis=1,ignore_index=False)
            self.data = self.data.loc[:,~self.data.columns.duplicated(keep='last')]
            
        if filetype == 'excel':
            self.data.to_excel(self.path)
        elif filetype == 'h5' or filetype == 'hdf':
            self.data.to_hdf(self.path,key='summary') 
        else:
            self.data.to_csv(self.path) 
        
    def read(self, warn=False):
        filetype = self.filetype
        if os.path.exists(self.path):
            if filetype == 'excel':
                data = pd.read_excel(self.path)
            elif filetype == 'h5' or filetype == 'hdf':
                data = pd.read_hdf(self.path,key='summary') 
            elif filetype == 'csv':
                pd.read_csv(self.path)
                data = pd.read_csv(self.path)
                data = data.drop(self.data.columns[0],axis=1)
        else:
            if warn:
                raise Warning("Summary file '%s' does NOT exist, returning empty DataFrame."%self.path)
            data = pd.DataFrame()
            
        # #### check for DataFrame Strings (NOT NEEDED ??????)
        # for col in self.data.columns:
        #     # float(self.summaryData.loc[col][0])
        #     if type(self.data[col][0]) is str:
        #         #### attempt to make it a DataFrame
        #         if '\n' in self.data[col][0]:
        #             try: 
        #                 value = pd.read_csv(io.StringIO(self.data[col][0]),delim_whitespace=True)
        #                 #value = value.set_index(value.columns[0])
        #                 self.data[col].loc[0] = value
        #             except:
        #                 if debug:
        #                     print('Unable to Coerce %s  to Dataframe'%(col))
        return data



if __name__ == "__main__":
    def costlyMethod():
        return (3,4)
    Cache = SoftCache()
    Cache.update({'a':1,'b':2})
    Cache.get(('c','d'),costlyMethod)
    print(Cache)
    value = Cache.get(('c',None),costlyMethod)
    print(value)
    print(Cache)
    # Sum = Summary(path='./processed/summary.h5')
    # a = {'var1':2.2,'var2':'red'}
    # Sum.add(a)
    # b = {'var3':1,'var4':True}
    # Sum.add(b)
    
    # print('Save data: \n%s\n'%Sum.data)
    # Sum.save()
    # data = Sum.read()
    # print('Read data: \n%s\n\nData Types:\n%s'%(data,data.dtypes))
    


