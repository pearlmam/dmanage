# -*- coding: utf-8 -*-


import threading
import time
from typing import  Dict, Any, List, Callable
from abc import ABC, abstractmethod
import weakref

__all__ = ["BaseScheduler", "Scheduler"]

class BaseScheduler(ABC):
    """Core scheduler engine handling background threads, job queues, and process cleanup."""

    def __init__(self, engine, max_concurrent_jobs: int = 2, poll_interval: float = 2.0):
        self.engine = engine
        self.jobs: Dict[str, Any] = {}
        self.max_concurrent_jobs = int(max_concurrent_jobs)
        self.max_concurrent_cores = 1
        self.poll_interval = poll_interval
        self.max_retries = 3
        self._running = True
        self._scheduler_thread = None
        # self._scheduler_thread.start()
        self._stop_event = threading.Event()
        self._start_scheduler_thread()
        # Finalizer handles both garbage collection (del) and process exit automatically.
        # No extra atexit registration needed as weakref.finalize handles atexit internally.
        self._finalizer = weakref.finalize(
            self,
            self._finalizer_routine,
            self.jobs,
            self.engine.terminate,  # Bound method of Engine (safe: Engine doesn't reference Scheduler)
            self._stop_event,
            self._scheduler_thread
        )

    # -------------------------------------------------------------------------
    # monitor thread managment
    # -------------------------------------------------------------------------
    @property
    def is_running(self):
        return self._scheduler_thread.is_alive() if hasattr(self._scheduler_thread, 'is_alive') else False
    
    def _start_scheduler_thread(self) -> None:
        """Starts monitoring thread without keeping a strong reference to self."""
        self._running = True
        if self.is_running:
            print("Scheduler is already started")
            return
        weak_self = weakref.ref(self)
        stop_event = self._stop_event
        
        def _thread_loop():
            while not stop_event.is_set():
                inst = weak_self()
                if inst is None or not inst._running:
                    break

                poll_interval = inst.poll_interval
                try:
                    inst._update_job_statuses()
                    inst._process_queue()
                except Exception as e:
                    print(f"Error in scheduler loop: {e}")

                # 1. CRITICAL: Drop local strong reference BEFORE thread sleeps/waits
                del inst

                # 2. Wait on event (unblocks instantly when finalizer sets stop_event)
                if stop_event.wait(timeout=poll_interval):
                    break
        # _thread_loop()
        self._scheduler_thread = threading.Thread(target=_thread_loop, daemon=True)
        self._scheduler_thread.start()
        return self.is_running
        
    def _stop_scheduler_thread(self, timeout: float = 5.0) -> bool:
        self._running = False
        start_time = time.time()
        while self._scheduler_thread.is_alive():
            if time.time() - start_time > timeout:
                break
            time.sleep(0.1)
        return self.is_running
    
    def _restart_scheduler(self) -> bool:
        self._stop_scheduler_thread()
        self._start_scheduler_thread()
        return self.is_running
    
    # -------------------------------------------------------------------------
    # Internal Loop & Queue Management
    # -------------------------------------------------------------------------
    
    def _start_job(self, job,**kwargs) -> None:
        job._pid = self.engine.launch(job,**kwargs)
        job.mark_started()
        
    def _kill_job(self, job,**kwargs) -> None:
        status = self.engine.terminate(job,**kwargs)
        job.mark_finished(status)
        # if status == "KILLED":
        self._cleanup_job_refs(job)
        
    def _poll_job(self, job: Any,**kwargs) -> Dict[str, Any]:
        """Polls an active process, updates status on completion, and cleans up handles."""
        try:
            if job.status == "RUNNING" and job._pid:
                status,ret_code = self.engine.get_status(job,**kwargs)
                if not (status == "RUNNING"):
                    job.exit_code = ret_code
                    job.mark_finished(status)
                    self._cleanup_job_refs(job)
        except Exception as e:
            print(f"Error polling status for active job '{job.job_id}': {e}")
            job.mark_finished("FAILED")
            job.exit_code = -1
            self._cleanup_job_refs(job) 
            
        return job.to_dict()

    def _update_job_statuses(self,**kwargs) -> None:
        """Updates status for all currently running jobs via _poll_job."""
        running_jobs = [j for j in self.jobs.values() if j.status == "RUNNING"]
        for job in running_jobs:
                self._poll_job(job,**kwargs)

    def _process_queue(self,**kwargs) -> None:
        """Launches queued jobs up to max slots with launch retry tracking."""
        running_jobs = [j for j in self.jobs.values() if j.status == "RUNNING"]
        queued_jobs = [j for j in self.jobs.values() if j.status == "QUEUED"]
        available_slots = int(self.max_concurrent_jobs - len(running_jobs))

        for job in queued_jobs[:available_slots]:
            try:
                self._start_job(job,**kwargs)
            except Exception as e:
                job.retry_count += 1
                self._cleanup_job_refs(job)

                if job.retry_count <= self.max_retries:
                    print(
                        f"Warning: Launch failed for job '{job.job_id}' "
                        f"({job.retry_count}/{self.max_retries}). Retrying... Error: {e}"
                    )
                else:
                    print(
                        f"Failed to launch job '{job.job_id}' after "
                        f"{self.max_retries} attempts: {e}"
                    )
                    job.mark_finished("FAILED")
                    job.exit_code = -1

    

    # -------------------------------------------------------------------------
    # Static Resource Cleanup Helpers
    # -------------------------------------------------------------------------
    
    def _cleanup_job_refs(self,job: Any) -> None:
        job._pid = None
        
    @staticmethod
    def _finalizer_routine(
        jobs: dict,
        terminate_func: Callable,
        stop_event: threading.Event,
        thread: threading.Thread | None
    ) -> None:
        """Static callback executed by weakref.finalize on 'del' or Python process exit."""
        # 1. Unblock the scheduler loop thread immediately
        if stop_event:
            stop_event.set()

        # 2. Kill all active process trees via Engine.terminate
        for job in list(jobs.values()):
            try:
                terminate_func(job, force=False)
            except Exception as e:
                print(f"Error terminating job {getattr(job, 'job_id', 'unknown')}: {e}")
            
            # Clean up job attributes
            if hasattr(job, "_pid"):
                job._pid = None

        # 3. Join the background thread cleanly
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        


class Scheduler(BaseScheduler):
    """User-facing management interface."""
    
    # -------------------------------------------------------------------------
    # Process & Job Controls
    # -------------------------------------------------------------------------

    def kill_job(self, job: str | Any, include_queued: bool = True, force: bool = False) -> Dict[str, Any]:
        """Kills a single job and updates handles/status."""
        job_obj = self.jobs[job] if isinstance(job, str) else job

        if job_obj.status == "RUNNING":
            self._kill_job(job_obj, force=force)
            job_obj.mark_finished("KILLED")
            self._cleanup_job_refs(job_obj)
        elif job_obj.status == "QUEUED" and include_queued:
            job_obj.mark_finished("KILLED")

        return job_obj.to_dict()

    def kill_active_jobs(self, include_queued: bool = True, force: bool = False) -> List[Dict[str, Any]]:
        """Kills all running and queued jobs."""
        for job in list(self.jobs.values()):
            self.kill_job(job, include_queued=include_queued, force=force)
        return [j.to_dict() for j in self.jobs.values()]

    def cleanup(self) -> None:
        """Full cleanup method for explicit or RPC invocations."""
        self.kill_active_jobs(force=True)
        self.stop_scheduler()
        if self._finalizer.alive:
            self._finalizer()

    # -------------------------------------------------------------------------
    # Daemon Lifecycle Controls
    # -------------------------------------------------------------------------

    def status(self) -> bool:
        return self.is_running

    def start(self) -> bool:
        return self._start_scheduler_thread()

    def stop(self, timeout: float = 5.0) -> bool:
        return self._stop_scheduler_thread()

    def restart(self) -> bool:
        return self._restart_scheduler_thread()
