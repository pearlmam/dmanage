# -*- coding: utf-8 -*-
import subprocess as sp
import os
import sys

try:
    import paramiko
except ImportError:
    raise ImportError("Module 'paramiko' must be installed to use the sync module, use 'pip install dmanage[paramiko]'")

from dmanage.utils.objinfo import is_iterable
def mkdirR(sftp, remote_directory):
    """Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created.
    """
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_directory == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory) # sub-directory exists
        
            
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdirR(sftp,dirname) # make parent directories
        sftp.mkdir(basename) # sub-directory missing, so created it
        sftp.chdir(basename)
        return True
    # print('directory exists: %s'%remote_directory)
    # # ??? delete contents
    # filesToRemove = self.sftp.listdir(path=remote_directory)
    # print('removing files: %s'%filesToRemove)
    # for file in filesToRemove:
    #     print('removing: %s'%(remote_directory+file))
    #     self.sftp.remove(remote_directory+file)
    
class DirSync():
    """This uses dirsync. Can only sync local dirs or mounted remote dirs 
    NOT USED< BUT I WANT TO KEEP
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
        import dirsync
        return dirsync.sync(source,dest,action=action,only=self.include)                
        
def rsync(source,dest,source_ssh=None,dest_ssh=None,options=['-am'],includes=["*.py","*/"],excludes=['*'],verbose=False):
    """Wrapper for the rsync terminal call
    
    The defaults include ONLY `.py` files!
    It does this by excluding all files, '*', and including only python 
    and directories,`["*.py","*/"]`. The -m option prevents creating empty directories.
    
    rsync options
    -a: --archive, do recursion
    -m: dont create empty directories
    -n: dont sync
    -ic: show changed files
    
    The dest directory MUST exist
    
    """
    if not is_iterable(options):
        options = [options]
    if not is_iterable(includes):
        includes = [includes]
    if not is_iterable(excludes):
        excludes = [excludes]
    
    
        
    # assemble ssh syntax
    if source_ssh is not None:
        source_rsync = source_ssh + ':' + source
    else:
        source_rsync = source
        
    if dest_ssh is not None:
        dest_rsync = dest_ssh + ':' + dest
    else:
        dest_rsync = dest
    
    # assemble options
    excludeOption = []
    for exclude in excludes:
        excludeOption = excludeOption + ['--exclude',exclude] 
    includeOption = []
    for include in includes:
        includeOption = includeOption + ['--include',include] 
    options = options + includeOption + excludeOption
    
    command = ['rsync'] + options + [source_rsync] + [dest_rsync]
    # command = ['sleep','1']
    if verbose: print(' '.join(command))
    proc = sp.Popen(command,stdout=sp.PIPE, stderr=sp.PIPE)
    proc.wait()
    errorOccurred = 0
    for line in proc.stdout.readlines():
        print(line.decode('ascii').rstrip('\n'))
    for line in proc.stderr.readlines():
        if 'failed: No such file or directory (2)' in line.decode('ascii').rstrip('\n'):
            errorOccurred = True
        print(line.decode('ascii').rstrip('\n'))
        
        errorOccurred = True
    if errorOccurred:
        # create dir because it doesnt exist
        print("Creating base directory: '%s'"%dest)
        if dest_ssh:
            userhost = dest_ssh.split('@')
            host = userhost[-1]
            if len(userhost)>1:
                user = userhost[0]
            else:
                user=None
            conn = paramiko.SSHClient()	# setup the client variable
            # allow modification of host_key.  This is the local list of allowed connections
            conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())	
            conn.connect(host, username=user)
            sftp = conn.open_sftp()
            mkdirR(sftp, dest)
            
            print("Attempting to re-sync...")
            proc = sp.Popen(command,stdout=sp.PIPE, stderr=sp.PIPE)
            
            proc.wait()
            for line in proc.stdout.readlines():
                print(line.decode('ascii').rstrip('\n'))
            for line in proc.stderr.readlines():
                print(line.decode('ascii').rstrip('\n'))
    return proc
