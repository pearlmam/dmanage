# -*- coding: utf-8 -*-
import os
import pandas as pd
import threading
import shutil
import filecmp

import atexit
from dmanage.utils.objinfo import is_iterable,is_primitive

from pathlib import Path
from dataclasses import dataclass
import json


__all__ = ["HardCache", "ParquetCache", "ZarrCache", "JSONCache", "SoftCache", "Summary"]

class SoftCache(dict):
    """This is a dict-like component used for storing data
    
    inherited arrays:
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
        Maybe for arrays returning tuples, have way to ignore some values using None
        
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
    
    def _get(self):
        """writen by child"""
        pass
    
    def get(self,key):
        """returns dict if list-like, else return value"""
        if isinstance(key,(tuple,list)):
            result = {}
            for k in key:
                result[k] = self._get(k)
            return result
        else:
            return self._get(key)
    
    def save(self,data,key,compression=None, thread=False):
        """Calls self._save() defined be baseclass
        
        Use the following code if thread check is neccessary:
            self._checkThreads(key)
            super().save(data,key,compression=compression,thread=thread)
        ??? Do I want to make this handle lists of data and keys???
        """
        if thread:
            kwargs={'data':data,'key':key,'compression':compression}
            t = threading.Thread(target=self._save,kwargs=kwargs)
            self._threads[key] = t
            t.start()
        else:
            self._save(data,key)
            
    def _save(self,data,key,compression=None):
        """writen by child"""
        pass
    
    def _checkThreads(self,key):
        """patiently waits for thread to finish writing before return
        currently no way to kill write thread.
        """
        if key in self._threads:
            t = self._threads[key]
            t.join()
            self._threads.pop(key)
    
    def flush(self):
        for key in self._threads:
            self._threads[key].join()
        self._threads.clear()
    
    def delete_all(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
    
    
    
    def duplicate(self,dst,protect=True):
        """duplicate the cache to another location"""
        dst = Path(dst)
        if dst.exists():
            if compare_dirs(self.path, dst,shallow=True):   # this compares the actual contents of the Cache
                # metadatas are identical so do  nothing
                return
            elif protect:
                # local metadata is protected, so raise error
                errormsg = (
                    "metadata already exists in path: '%s', "%dst +
                    "to overwrite, set 'protect=False'"
                    )
                raise FileExistsError(errormsg)
            else:
                # metadata is unprotected, so delete data
                shutil.rmtree(dst)
        # data doesnt exist or is unprotected
        return shutil.copytree(self.path, dst)

     
    def __exit__(self):
        self.flush()
        
@dataclass(frozen=True)
class GroupInfo:
    """This may be used for unified cache to dispatch appropriate caching method...
    """
    path: Path
    ext: str
    
    def file(self,key: str) -> Path:
        return self.path / f"{key}.{self.ext}"
  
# define supported types
# self.groups = {
#     'DataFrame':GroupInfo(
#         path = self.path / 'dfs/',
#         ext = 'par',
#         ),
#     'Series':GroupInfo(
#         path = self.path / 'series/',
#         ext = 'par',
#         ),
#     'array':GroupInfo(
#         path = self.path / 'arrays/',
#         ext = 'par',
#         ),
#     'primitive':GroupInfo(
#         path = self.path / 'primitives/',
#         ext = 'json',
#         ),
#     'container':GroupInfo(
#         self.path / 'containers/',
#         ext = 'json',
#         )
#     }
  
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
        self.groups = {
            'DataFrame':self.path / 'dfs/',
            'Series':self.path / 'series/',
            'array':self.path / 'arrays/'
            }
                
            
    def keys(self,kind='all'):
        """Gets the keys of data of type 'kind'"""
        if kind == "all":
            out = {}
            for k in self.groups:
                path = self.groups[k]
                if not path.exists():
                    out[k] = []
                    continue
                out[k] = [p.stem for p in path.glob("*.par")]
            return out
        
        path = self.groups[kind]
        if not path.exists():
            return []
        return [p.stem for p in path.glob("*.par")]
    
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
    
    def save(self,data,key,compression=None, thread=False):
        self._checkThreads(key)
        super().save(data,key,compression=compression,thread=thread)
        # super()._save(data,key,compression=None)
    
    def _save(self,data,key,compression=None):
        if self.debug: print("Writing '%s'"%key)
        if compression is None:
            compression = self.compression
        #print('writing %s'%key)
        if isinstance(data,(pd.core.frame.DataFrame)):
            writePath = self._path( key, 'DataFrame')
        elif isinstance(data,pd.core.series.Series):
            writePath = self._path( key, 'Series')
            if data.name is None:
                data.name = 'data'
            data = data.to_frame()
        
        # atomic write to prevent trying to read corrupted data  
        writePath.parent.mkdir(parents=True, exist_ok=True)
        tmpPath = str(writePath) + '.tmp'
        # path.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(tmpPath,compression=compression)
        os.replace(tmpPath, writePath)
        if self.debug: print("Done with: '%s'"%key)  
        
    def _path(self, key, grp):
        base = self.groups[grp] 
        return base / f"{key}.par"   
    
    def remove(self,key):
        """needs implementation"""
        grp = self.keys_flat().get(key,None)
        if grp is not None:
            os.remove(self.groups[grp].file(key))
        else:
            raise Warning("No '%s' in Hard Cache, ignoring... Availiable keys: %s"%(key,self.keys()))
        
    def _get(self,key,method=None,*args,**kwargs):
        self._checkThreads(key)
        if self.debug: print("Getting '%s'"%key)
        grp = self.keys_flat().get(key,None)   # return None if not in keys
        if grp is None:
            if method is not None:
                data = method(*args, **kwargs)
                self.save(data)
            else:
                data = None
        elif grp == 'DataFrame':
            data = pd.read_parquet(self._path(key, grp))
        elif grp == 'Series':
            data = pd.read_parquet(self._path(key, grp))
            data = data.iloc[:,0]
        else:
            data = None
            # raise Exception("No '%s' in keys and method=None, Define method to generate and hard cache the data."%(key))
        return data
    
    
    
class JSONCache(HardCache):
    def __init__(self,path='./cache.json',debug=False):
        super().__init__(path)
        self.debug = debug
        self.groups = {
            'primitive':self.path / "primitive",
            'container':self.path / "container"
            }
        
        self.groups['primitive'].mkdir(parents=True, exist_ok=True)
        self.groups['container'].mkdir(parents=True, exist_ok=True)
    
    def keys(self,kind='all'):
        """Gets the keys of data of type 'kind'"""
        if kind == "all":
            out = {}
            for k in self.groups:
                path = self.groups[k]
                if not path.exists():
                    out[k] = []
                    continue
                out[k] = [p.stem for p in path.glob(f"*.json")]
            return out
        
        path = self.groups[kind]
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
    
    def _save(self,data,key):
        payload, kind = self.encode(data)
        path = self._path(key, kind)
        tmp = path.with_suffix(".json.tmp")
    
        with tmp.open("w") as f:
            json.dump(payload, f, indent=2)
        tmp.replace(path)
    
    def _get(self,key,method=None,*args,**kwargs):
        if self.debug: print("Getting '%s'"%key)
        grp = self.keys_flat().get(key,None)   # return None if not in keys
        if grp is None:
            if method is not None:
                data = method(*args, **kwargs)
                self.save(data)
            else:
                data = None
        elif grp is not None:
            base = self.groups[grp]
            path = base / f"{key}.json"
            with path.open() as f:
                data = self.decode(json.load(f))
        else:
            data = None
            # raise Exception("No '%s' in keys and method=None, Define method to generate and hard cache the data."%(key))
        return data
    
    def _path(self, key, kind):
        base = self.groups[kind]
        return base / f"{key}.json"   
    
    def encode(self,obj):
        if is_primitive(obj) or obj is None:
            return obj, "primitive"
    
        if isinstance(obj, tuple):
            return {"__type__": "tuple", "value": list(obj)}, "container"
    
        if isinstance(obj, set):
            return {"__type__": "set", "value": list(obj)}, "container"
    
        if isinstance(obj, (list, dict)):
            return obj, "container"
    
        raise TypeError(f"JSON cannot encode {type(obj)}")
        
    def decode(self,obj):
        if isinstance(obj, dict) and "__type__" in obj:
            t = obj["__type__"]
            if t == "tuple":
                return tuple(obj["value"])
            if t == "set":
                return set(obj["value"])
        return obj
    

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
             
    def save(self,data,key,thread=False):
        """No thread check neccessary because zarr will just stop other thread and overwrite"""
        if thread:
            kwargs={'data':data,'key':key}
            t = threading.Thread(target=self._save,kwargs=kwargs)
            self._threads[key] = t
            t.start()
        else:
            self._save(data,key)
    
    def _save(self,data,key):
        """ Called from HardCache.save()
        No thread check neccessary because zarr will just stop other thread and overwrite"""
        #print('writing %s'%key)
        if isinstance(data,(pd.core.frame.DataFrame)):
            xs = data.to_xarray()
            xs.attrs['dtype'] = 'DataFrame'
        elif isinstance(data,pd.core.series.Series):
            xs = data.to_xarray()
            xs = xs.to_dataset(name=getattr(xs,key,'data'))
            xs.attrs['dtype'] = 'Series'
        xs.to_zarr(store=self.path,group=key, mode="w", consolidated=True)
            
    def remove(self,key):
        if key in self.root:
            del self.root[key]
        else:
            raise Warning("No '%s' in Hard Cache, ignoring... Availiable keys: %s"%(key,self.keys()))
        
    def _get(self,key,method=None,*args,**kwargs):
        """
        zarr inherently has read blocking until done writing, but if the read is too soon,
        It will get corrupted data; thats why thread checking is performed here.
        """
        
        self._checkThreads(key)
        if key in self.root:
            grp = self.root[key]
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
            # raise Exception("No '%s' in keys and method=None, Define method to generate and hard cache the data."%(key))
        return data

class Summary():
    """This manages summary data in RAM and on the disk
    """
    def __init__(self,path='./processed/summary.csv'):
        
        path = Path(path)
        if path.suffix in ['.csv','.h5','xlsx']:
            self.filetype = path.suffix[1:]
        else:
            self.filetype = 'csv'
            path = path / 'summary.csv'
          
        self.path = path
        self.loc = path.parent
        self.data = pd.DataFrame()
        
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
        if not self.loc.is_dir():
            os.mkdir(self.loc)
        if not ow:
            data = self.read(warn=False)
            self.data = pd.concat([self.data.reset_index(drop=True),data.reset_index(drop=True)],axis=1,ignore_index=False)
            self.data = self.data.loc[:,~self.data.columns.duplicated(keep='last')]
            
        if filetype == 'xlsx':
            self.data.to_excel(self.path)
        elif filetype == 'h5' or filetype == 'hdf':
            self.data.to_hdf(self.path,key='summary') 
        else:
            self.data.to_csv(self.path) 
        
    def read(self, warn=False):
        filetype = self.filetype
        if os.path.exists(self.path):
            if filetype == 'xlsx':
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


######## helper
# class dircmp(filecmp.dircmp):
#     """
#     Workaround for Python 3.12 and below
#     Compare the content of dir1 and dir2. In contrast with filecmp.dircmp, this
#     subclass compares the content of files with the same path.
#     """
#     def phase3(self):
#         """
#         Find out differences between common files.
#         Ensure we are using content comparison with shallow=False.
#         """
#         fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files,
#                                  shallow=False)
#         self.same_files, self.diff_files, self.funny_files = fcomp


def compare_dirs(dir1, dir2,shallow=True):
    """
    Compare two directory trees content.
    Return False if they differ, True is they are the same.
    """
    # compared = dircmp(dir1, dir2)  # I think this is uneeded with python 3.13+
    compared = filecmp.dircmp(dir1, dir2,shallow=shallow)
    if (compared.left_only or compared.right_only or compared.diff_files 
        or compared.funny_files):
        return False
    for subdir in compared.common_dirs:
        if not compare_dirs(os.path.join(dir1, subdir), os.path.join(dir2, subdir),shallow=shallow):
            return False
    return True

# def compare_dirs(dir1, dir2, shallow=False):
#     """
#     Fast recursive directory comparison. from chatGPT
#     Returns True if directories are identical, False otherwise.
#     """

#     stack = [(dir1, dir2)]

#     while stack:
#         d1, d2 = stack.pop()

#         try:
#             entries1 = set(os.listdir(d1))
#             entries2 = set(os.listdir(d2))
#         except OSError:
#             return False

#         # different directory contents
#         if entries1 != entries2:
#             return False

#         for name in entries1:
#             p1 = os.path.join(d1, name)
#             p2 = os.path.join(d2, name)

#             if os.path.isdir(p1):
#                 if not os.path.isdir(p2):
#                     return False
#                 stack.append((p1, p2))

#             else:
#                 if not os.path.isfile(p2):
#                     return False

#                 # if not filecmp.cmp(p1, p2, shallow=shallow):
#                 #     return False
#                 if not filecmp.cmp(p1, p2, shallow=True):
#                     # check the file 
#                     if not filecmp.cmp(p1, p2, shallow=False):
#                         return False

#     return True



if __name__ == "__main__":
    def costlyMethod():
        return (3,4)
    # Cache = SoftCache()
    # Cache.update({'a':1,'b':2})
    # Cache.get(('c','d'),costlyMethod)
    # print(Cache)
    # value = Cache.get(('c',None),costlyMethod)
    # print(value)
    # print(Cache)
    # Sum = Summary(path='./processed/summary.h5')
    # a = {'var1':2.2,'var2':'red'}
    # Sum.add(a)
    # b = {'var3':1,'var4':True}
    # Sum.add(b)
    
    # print('Save data: \n%s\n'%Sum.data)
    # Sum.save()
    # data = Sum.read()
    # print('Read data: \n%s\n\nData Types:\n%s'%(data,data.dtypes))
    
    Cache = JSONCache()
    Cache.save(3, 'three')
    Cache.save(((186, 462), (1805, 462)), 'activeRegion')
    
    value = Cache.get('activeRegion')
    print(Cache.keys())
    print(Cache.keys_flat())

