# -*- coding: utf-8 -*-

import subprocess as sp

""" UNDER DEVELOPMENT, This template uses subprocess to submit and monitor jobs
In the future, an RPC server should be used to submit and monitor jobs,
and this script will interact with that.
"""

class JobSubmit():
    def __init__(self, programDir='path/to/executable',unloadModules=[],loadModules=[],maxProcs=32):
        # setup variables neccessary for running executable
        pass
    
    def submit_job(self,jobLoc,nc,):
        """submit job to run
        
        Parameters
        ----------
        jobLoc : str
            Where the run files exist and where generated data will be stored.
        nc : int
            number of cores to use.
    
        Returns
        -------
        None.
    
        """
        pass
    
    def submit_jobs(self, jobLocs, nc, nt):
        """submit multiple jobs
        This will submit multiple jobs to run, monitor the progress, and submit 
        new jobs as processes finish

        Parameters
        ----------
        jobLocs : list of str
            Where the run files are.
        nc : int
            number of cores to use for each job.
        nt : int
            number of threads; used to jun multiple jobs concurrently.

        Returns
        -------
        None.

        """
        pass
    
    def check_progress(self,proc):
        """Check the progress of the job
        Use this to determine when jobs finish

        Parameters
        ----------
        proc : subprocess.Thread
            The Thread object created by subprocess module.

        Returns
        -------
        None.

        """
        
        