# -*- coding: utf-8 -*-
  

from typing import Optional, Dict, Any, List
import inspect
import json
from pathlib import Path
import os
import uuid

import dmanage.metadata.metastring as meta
from .scheduler import Scheduler
from .job import Job,PrettyList

try:
    import Pyro5.api
    pyro_expose = Pyro5.api.expose
    pyro_behavior = Pyro5.server.behavior
except ImportError:
    # No-op decorator if Pyro5 is not installed
    def pyro_expose(obj):
        return obj
    # No-op decorator factory (accepts configuration args, returns decorator)
    def pyro_behavior(*args, **kwargs):
        return lambda obj: obj

__all__ = ["load_job_config", "Dispatcher","pyro_expose","pyro_behavior"]


def load_job_config(inject_globals: bool = True, require_existing: bool = True) -> dict:
    config_raw = os.environ.get("JOB_CONFIG", "{}")
    config = json.loads(config_raw)

    is_managed = config.pop("_managed", False)

    # Return cleanly if run from terminal OR if scheduler passed no parameter overrides
    if not is_managed or not config:
        return {}

    if inject_globals:
        caller_globals = inspect.currentframe().f_back.f_globals
        modified_count = 0

        for key, new_val in config.items():
            if require_existing and key not in caller_globals:
                raise KeyError(
                    f"Parameter '{key}' in JOB_CONFIG is not defined in the input script. "
                    "Ensure default values are declared in the script before calling load_job_config()."
                )

            if caller_globals.get(key) != new_val:
                caller_globals[key] = new_val
                modified_count += 1

        if modified_count == 0:
            pass
            # raise ValueError(
            #     "JOB_CONFIG parameters were passed, but 0 global variables were modified "
            #     "(the overrides passed were identical to the script's hardcoded defaults)."
            # )

    return config

@pyro_expose
@pyro_behavior(instance_mode="single")
class Dispatcher():
    def __init__(self,engine,run_base_dir=None,max_concurrent_jobs = 2, poll_interval = 2.0):
        
        self.model_include_patterns = None
        self.model_ignore_patterns = ["__pycache__", "*.pyc", "*.log", ".git","*.h5","*.png"]
        defualt_base_dir = Path.home() / "Documents" / "data"
        self.run_base_dir = Path(run_base_dir) if run_base_dir else defualt_base_dir
        self.scheduler = Scheduler(engine,max_concurrent_jobs, poll_interval)
        self.jobs = self.scheduler.jobs    # currently a copy for convenience
    
    
    def _compose_path(self,params, equiv='-', sep='/', order=False,format=None,numDecimals=3):
        run_base_dir = Path(self.run_base_dir)
        if meta:
            tail_path = Path(meta.compose(params,equiv, sep, order,format,numDecimals) )
        else:
            raise ModuleNotFoundError("package dmanage is required to automatically compose paths, you must specify the 'run_path' for each job.")
        return run_base_dir / tail_path
    
    ##########################
    # Job Managment
    ##########################
    @pyro_expose
    def create_job(self, model_path: str,
                   run_path: str = None,
                   job_params: Dict = None,
                   job_config_path: Optional[Path] = None,
                   job_id: Optional[str] = None,
                   nc: Optional[int] = 1,
                   ) -> Dict[str, Any]:
        
        if not run_path and not job_params:
            raise TypeError("Either 'run_path' or 'job_params' must be defined")
        elif run_path and job_params:
            pass
        elif job_params:
            run_path = self._compose_path(job_params)
        
        
        """Creates a job using an optional custom ID or an auto-generated UUID."""
        actual_id = job_id or self._generate_job_id()

        if actual_id in self.jobs:
            raise ValueError(f"Job ID '{actual_id}' already exists.")
        if run_path in self.get_run_paths():
            raise ValueError(f"Run path '{run_path}' already exists in one or more jobs.")
        # job = Job.from_config_file(actual_id, job_config_path)
        job = Job(
            job_id = actual_id, 
            model_path=model_path,
            run_path=run_path,
            params=job_params,
            nc=nc,
            model_include_patterns = self.model_include_patterns,
            model_ignore_patterns = self.model_ignore_patterns,
            )
        self.jobs[actual_id] = job
        return job.to_dict()
    
    @pyro_expose
    def set_job_params(
        self,
        job: str | Job,
        params: Optional[Dict[str, Any]] = None,
        nc: Optional[int] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """Updates job parameters and core count.
        
        By default (overwrite=False), new parameters are merged into existing ones.
        Set overwrite=True to wipe existing parameters and replace them completely.
        """
        job = self.jobs[job] if isinstance(job, str) else job
    
        if job.status in ("RUNNING", "COMPLETED", "FAILED", "KILLED"):
            raise ValueError(f"Cannot modify parameters for job in '{job.status}' state.")
    
        # Update core count if provided
        if nc is not None:
            job.nc = nc
    
        # Update or overwrite parameters dictionary
        if params is not None:
            if overwrite:
                job.params = dict(params)
            else:
                job.params.update(params)
    
        return job.to_dict()
    
    @pyro_expose
    def submit_job(self, job: str | Job, nc: [int] = None):
        if not self.scheduler.is_running:
            raise Exception("The scheduler is NOT running! Start the scheduler before submiting jobs.")
        job = self.jobs[job] if isinstance(job, str) else job
        #### check for issues
        if not job:
            raise ValueError(f"Job {job} not found.")
        if nc:
            job.nc = nc
        job.status = "QUEUED"
        
    @pyro_expose
    def submit_pending(self):
        for job in self.jobs.values():
            if job.status == "PENDING":
                job.status = "QUEUED"
                
    @pyro_expose
    def kill_job(self, *args, **kwargs):
        # Optional pre-processing or logging
        return self.scheduler.kill_job(*args, **kwargs)
    
    @pyro_expose
    def kill_active_jobs(self, *args, **kwargs):
        return self.scheduler.kill_active_jobs( *args, **kwargs) 
    
    @pyro_expose
    def clear_jobs(self, include_queued: bool = False) -> List[Dict[str, Any]]:
        """Removes finished jobs (and optionally queued/pending jobs) from memory."""
        # self.scheduler._update_job_statuses()
    
        keys_to_remove = [
            job_id for job_id, job in self.jobs.items()
            if job.status in ("COMPLETED", "FAILED", "KILLED")
            or (include_queued and job.status in ("PENDING", "QUEUED"))
        ]
    
        for job_id in keys_to_remove:
            del self.jobs[job_id]
    
        return self.get_jobs()

    ##########################
    # exposed getters
    ##########################
    @pyro_expose
    def get_jobs(self):
        output = PrettyList([])
        for job in self.jobs.values():
            output.append(job.to_dict())
        return output
    
    @pyro_expose
    def get_run_paths(self):
        output = []
        for job in self.jobs.values():
            output.append(str(job.run_path))
        return output 
    
    @pyro_expose
    def get_ids(self):
        output = []
        for job in self.jobs.values():
            output.append(str(job.job_id))
        return output 
    
    @pyro_expose
    def get_run_base_dir(self):
        return self.run_base_dir
    
    ##########################
    # exposed setters
    ##########################
    
    @pyro_expose
    def set_run_base_dir(self,run_base_dir):
        self.run_base_dir = run_base_dir

    def _generate_job_id(self, prefix: str = "job") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    ##########################
    # scheduler Methods
    ##########################
    @pyro_expose
    def scheduler_status(self) -> bool:
        return self.scheduler.status()
    
    @pyro_expose
    def start_scheduler(self) -> bool:
        return self.scheduler.start()
    
    @pyro_expose
    def stop_scheduler(self, timeout: float = 5.0) -> bool:
        return self.scheduler.stop()

    @pyro_expose
    def restart_scheduler(self) -> bool:
        return self.scheduler.restart()

    # -------------------------------------------------------------------------
    # Configuration Setters
    # -------------------------------------------------------------------------
    @pyro_expose
    def set_poll_interval(self, poll_interval: float) -> None:
        self.scheduler.poll_interval = poll_interval
        
    @pyro_expose
    def set_max_concurrent_jobs(self, max_concurrent_jobs: int) -> None:
        self.scheduler.max_concurrent_jobs = max_concurrent_jobs
        
    @pyro_expose
    def set_max_concurrent_cores(self, max_concurrent_cores: int) -> None:
        self.scheduler.max_concurrent_cores = max_concurrent_cores
    
  
    def shutdown(self):
        self.scheduler.cleanup()
    
if __name__ == "__main__":
    pass