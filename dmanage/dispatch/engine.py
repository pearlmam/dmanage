# -*- coding: utf-8 -*-

import signal
import os
from abc import ABC, abstractmethod
from .job import Job
import subprocess
import shutil
from pathlib import Path

__all__ = ["ExecutionEngine", "SubProcEngine"]
class ExecutionEngine(ABC):

    @abstractmethod
    def launch(self, job):
        """Starts the job and returns a unique identifier (PID or PBS_ID)."""
        pass


    @abstractmethod
    def get_status(self, job) :
        """Returns True if the job is still running, False if finished."""
        pass

    def get_ret_code(self,job):
        pass

    def terminate(self,job):
        pass
    
    def cleanup_references(job: Job) -> None:
        pass
    
    def setup_workspace(self, job) -> Path:
        pass


# class WarpXEngine(ExecutionEngine):

class SubProcEngine(ExecutionEngine):
    def __init__(self):
        self._procs: dict[str, subprocess.Popen] = {}
        
    def get_status(self, job) :
        """Returns True if the job is still running, False if finished."""
        proc = self._procs.get(job.job_id)
        if proc is None:
            return "UNKNOWN", None
        
        return_code = proc.poll()
        if return_code is None:
            return "RUNNING", None
        
        # Cleanup internal reference when finished
        del self._procs[job.job_id]
        status = "COMPLETED" if return_code == 0 else "FAILED"
        return status, return_code

    def terminate(self,job,force: bool = False, timeout: float = 3.0) -> None:
        """Recursively kills the entire process tree (mpiexec + child python processes)."""
        proc = self._procs.get(job.job_id)
        if not proc or proc.poll() is not None:
            return "UNKNOWN"

        # Attempt process tree kill via psutil (handles mpiexec + spawned workers)
        try:
            import psutil
            parent = psutil.Process(proc.pid)
            children = parent.children(recursive=True)

            for child in children:
                if force:
                    child.kill()
                else:
                    child.terminate()

            if force:
                parent.kill()
            else:
                parent.terminate()

        except ImportError:
            # Fallback to OS process group kill if psutil isn't installed
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL if force else signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        except Exception:
            pass
        return "KILLED"


    def setup_workspace(self, job) -> Path:
        source_dir,_ =  job.check_model_path()
        job.check_run_path()
        run_dir = job.run_path
        job.run_path.mkdir(parents=True, exist_ok=True)
    
        if job.model_include_patterns:
            # Pattern-based copying: Grab only matching files
            for pattern in job.model_include_patterns:
                for source_file in source_dir.glob(pattern):
                    if source_file.is_file():
                        shutil.copy2(source_file, run_dir / source_file.name)
        else:
            # Whole-directory copying: Copy everything except ignored patterns
            ignore_func = shutil.ignore_patterns(*(job.model_ignore_patterns or []))
            shutil.copytree(source_dir, run_dir, dirs_exist_ok=True, ignore=ignore_func)
    
        return run_dir

   

