# -*- coding: utf-8 -*-


from dirsync import sync
import subprocess as sp

class DirSync():
    """This uses dirsync. Can only sync local dirs or mounted remote dirs 
    """    
    
    def __init__(self,source,target,keep=".py",ignore=None):
        self.source = source
        self.target = target
        self.include = ('^.*\\.py$',)
        # easier to use keep python files only
        self.ignoreHidden = "/\\."     # hidden files with "." prefix
        self.ignoreCache = "/_"        # hidden files with "_" prefix
        self.ignoreLogs = ("nohup", ".log",)
    
    def sync(self,source,dest,action='sync'):
        return sync(source,dest,action=action,only=self.include)                
        
def rsync(source,dest,source_ssh=None,dest_ssh=None,options='-am',includes=["*.py","*/"],excludes=['*'],verbose=False):
    """Wrapper for the rsync terminal call
    
    The defaults include ONLY '.py' files! 
    It does this by excluding all files, '*', and including only python 
    and directories,["*.py","*/"]. The -m option prevents creating empty directories.
    
    rsync options
    -a: --archive, do recursion
    -m: dont create empty directories
    -n: dont sync
    -ic: show changed files
    
    """
    # assemble ssh syntax
    if source_ssh is not None:
        source = source_ssh + ':' + source
    
    if dest_ssh is not None:
        dest = dest_ssh + ':' + dest
    
    # assemble options
    excludeOption = []
    for exclude in excludes:
        excludeOption = excludeOption + ['--exclude',exclude] 
    includeOption = []
    for include in includes:
        includeOption = includeOption + ['--include',include] 
    options = [options] + includeOption + excludeOption
    
    command = ['rsync'] + options + [source] + [dest]
    if verbose: print(command)
    output = sp.Popen(command)
    
    return output
