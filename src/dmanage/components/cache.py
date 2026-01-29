# -*- coding: utf-8 -*-
import os
import pandas as pd
import threading
import shutil

import atexit
from dmanage.utils.objinfo import is_iterable
from pathlib import Path
from dataclasses import dataclass


__all__ = ["HardCache", "ParquetCache", "ZarrCache", "SoftCache", "Summary"]

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

class HardCache:
    """Base class for hard caches"""
    def __init__(self,path):
        self.path = Path(path)
        self._threads = {}
        atexit.register(self.flush)  # ensures flush when program terminates.
    
    def keys(self):
        """writen by child"""
        pass
    
    def get(self):
        """writen by child"""
        pass
    
    def save(self,data,name,compression=None, thread=False):
        """Calls self._save() defined be baseclass
        Use the following if thread check is neccessary:
            self._checkThreads(name)
            super().save(data,name,compression=compression,thread=thread)
        
        """
        if thread:
            kwargs={'data':data,'name':name,'compression':compression}
            t = threading.Thread(target=self._save,kwargs=kwargs)
            self._threads[name] = t
            t.start()
        else:
            self._save(data,name)
            
    def _save(self,data,name,compression=None):
        """writen by child"""
        pass
    
    def _checkThreads(self,name):
        """patiently waits for thread to finish writing before return
        currently no way to kill write thread.
        """
        if name in self._threads:
            t = self._threads[name]
            t.join()
            self._threads.pop(name)
    
    def flush(self):
        for key in self._threads:
            self._threads[key].join()
        self._threads.clear()
    
    def delete_all(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
    
    def __exit__(self):
        self.flush()
        
@dataclass(frozen=True)
class GroupInfo:
    path: Path
    ext: str
    
    def file(self,name: str) -> Path:
        return self.path / f"{name}.{self.ext}"
    
class ParquetCache(HardCache):
    """
    this needs to block reads until write is finished: No inherit blocking.
    The atomic write requires thread blocking on save
    """
    
    def __init__(self,path='./cache.parq',compression ="snappy",debug=False):
        super().__init__(path)
        
        try: 
            os.mkdir(path)
        except:
            pass
        
        self.compression = compression
        self.debug = debug
        # define supported types
        self.groups = {
            'DataFrame':GroupInfo(
                path = self.path / 'dfs/',
                ext = 'par',
                ),
            'Series':GroupInfo(
                path = self.path / 'series/',
                ext = 'par',
                ),
            'array':GroupInfo(
                path = self.path / 'arrays/',
                ext = 'par',
                ),
            'literal':GroupInfo(
                path = self.path / 'literals/',
                ext = 'json',
                ),
            'container':GroupInfo(
                self.path / 'containers/',
                ext = 'json',
                )
            }

    def keys(self,kind='all'):
        """Gets the keys of data of type 'kind'"""
        if kind == "all":
            out = {}
            for k in self.groups:
                path = self.groups[k].path
                if not path.exists():
                    out[k] = []
                    continue
                ext = self.groups[k].ext
                out[k] = [p.stem for p in path.glob(f"*{ext}")]
            return out
        
        path = self.path / self.groups[kind]
        if not path.exists():
            return []
        return [p.stem for p in path.glob(".%s"%self.exts[kind])]
    
    def keys_flat(self):
        flat = {}
        grouped = self.keys(kind="all")
    
        for kind, keys in grouped.items():
            for key in keys:
                if key in flat:
                    raise ValueError(
                        f"Key '{key}' exists in multiple kinds: "
                        f"{flat[key]} and {kind}"
                    )
                flat[key] = kind
        return flat
    
    def save(self,data,name,compression=None, thread=False):
        self._checkThreads(name)
        super().save(data,name,compression=compression,thread=thread)
        # super()._save(data,name,compression=None)
    
    def _save(self,data,name,compression=None):
        if self.debug: print("Writing '%s'"%name)
        if compression is None:
            compression = self.compression
        #print('writing %s'%name)
        if isinstance(data,(pd.core.frame.DataFrame)):
            writePath = self.groups['DataFrame'].file(name)
        elif isinstance(data,pd.core.series.Series):
            writePath = self.groups['Series'].file(name)
            if data.name is None:
                data.name = 'data'
            data = data.to_frame()
        
        # atomic write to prevent trying to read corrupted data  
        writePath.parent.mkdir(parents=True, exist_ok=True)
        tmpPath = str(writePath) + '.tmp'
        # path.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(tmpPath,compression=compression)
        os.replace(tmpPath, writePath)
        if self.debug: print("Done with: '%s'"%name)  
        
    def remove(self,name):
        """needs implementation"""
        grp = self.keys_flat().get(name,None)
        if grp is not None:
            os.remove(self.groups[grp].file(name))
        else:
            raise Warning("No '%s' in Hard Cache, ignoring... Availiable keys: %s"%(name,self.keys()))
        
    def get(self,name,method=None,*args,**kwargs):
        self._checkThreads(name)
        if self.debug: print("Getting '%s'"%name)
        grp = self.keys_flat().get(name,None)   # return None if not in keys
        if grp is None:
            if method is not None:
                data = method(*args, **kwargs)
                self.save(data)
            else:
                data = None
        elif grp == 'DataFrame':
            data = pd.read_parquet(self.groups[grp].file(name))
        elif grp == 'Series':
            data = pd.read_parquet(self.groups[grp].file(name))
            data = data.iloc[:,0]
        else:
            data = None
            # raise Exception("No '%s' in keys and method=None, Define method to generate and hard cache the data."%(name))
        return data

class ZarrCache(HardCache):
    """This is a component that stores data in an zarr file on the disk

    """
    def __init__(self,path='./cache.zarr'):
        try:
            import zarr
            import xarray
            self._zarr = zarr
            self._xr = xarray
        except ImportError as e:
            raise ImportError(
                "HardCache requires the 'zarr' and 'xarray' package. "
                "Install it with: pip install dmanage['hardcache']"
            ) from e
        super().__init__(path)
        try:
            self.root = self._zarr.open(self.path,mode='r')
        except:
            self.root = self._zarr.open(self.path,mode='w')
            self.root = self._zarr.open(self.path,mode='r')
    
    def keys(self):
        """Gets the keys of the availiable data"""
        return list(self.root.group_keys())
             
    def save(self,data,name,thread=False):
        """No thread check neccessary because zarr will just stop other thread and overwrite"""
        if thread:
            kwargs={'data':data,'name':name}
            t = threading.Thread(target=self._save,kwargs=kwargs)
            self._threads[name] = t
            t.start()
        else:
            self._save(data,name)
    
    def _save(self,data,name):
        """ Called from HardCache.save()
        No thread check neccessary because zarr will just stop other thread and overwrite"""
        #print('writing %s'%name)
        if isinstance(data,(pd.core.frame.DataFrame)):
            xs = data.to_xarray()
            xs.attrs['dtype'] = 'DataFrame'
        elif isinstance(data,pd.core.series.Series):
            xs = data.to_xarray()
            xs = xs.to_dataset(name=getattr(xs,name,'data'))
            xs.attrs['dtype'] = 'Series'
        xs.to_zarr(store=self.path,group=name, mode="w", consolidated=True)
            
    def remove(self,name):
        if name in self.root:
            del self.root[name]
        else:
            raise Warning("No '%s' in Hard Cache, ignoring... Availiable keys: %s"%(name,self.keys()))
        
    def get(self,name,method=None,*args,**kwargs):
        """
        zarr inherently has read blocking until done writing, but if the read is too soon,
        It will get corrupted data; thats why thread checking is performed here.
        """
        
        self._checkThreads(name)
        if name in self.root:
            grp = self.root[name]
            if grp.attrs.get("dtype") == 'DataFrame':
                data = self._xr.open_zarr(store=grp.store,group=grp.path)
                data = data.to_dataframe()
            elif grp.attrs.get("dtype") == 'Series':
                data = self._xr.open_zarr(store=grp.store,group=grp.path)
                data = data.to_dataframe().iloc[:,0]
            else:
                data = None
        elif method is not None:
            data = method(*args, **kwargs)
            self.save(data)
        else:
            data = None
            # raise Exception("No '%s' in keys and method=None, Define method to generate and hard cache the data."%(name))
        return data

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
    


