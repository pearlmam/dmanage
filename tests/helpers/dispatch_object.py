# -*- coding: utf-8 -*-

import json
import os
from dmanage.dispatch import SubProcEngine, Dispatcher,pyro_behavior,pyro_expose
import subprocess
from pathlib import Path
import shutil

class TestEngine(SubProcEngine):
    def launch(self, job):
        """RPC endpoint to launch the simulation process."""
        
        run_dir = str(self.setup_workspace(job))
        
        #### open log file
        if job.log_path:
            job.log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = open(job.log_path, "w")
        
        #### generate run command
        command = []
        if job.nc>1:
            # command.extend(['mpiexec','-x', 'JOB_CONFIG','-np','%i'%job.nc])
            command.extend(['mpiexec','-np','%i'%job.nc])
        command.extend(['python',job.model_path.name])
        
        #### run job
        env = self._set_run_env(job)   # to pass arguments to simulation
        proc = subprocess.Popen(
            command,
            cwd=run_dir,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,  # Redirect stderr into stdout
            start_new_session=True     # Decouples process group for clean killing
            )
        
        if log_file:
            log_file.close()
                
        self._procs[job.job_id] = proc
        return str(proc.pid)
    
    def _set_run_env(self, job):
        params = getattr(job, "parameters", getattr(job, "params", {})).copy()
        params["_managed"] = True # flag to tell load_job_config JOB_CONFIG is neccessary
        
        job_config_json = json.dumps(params, default=str)
        return {**os.environ, "JOB_CONFIG": job_config_json}
    
    
@pyro_expose
@pyro_behavior(instance_mode="single")
class TestDispatcher(Dispatcher):
    def __init__(self, run_base_dir = None, max_concurrent_jobs: int = 2, poll_interval: float = 1.0):
        super().__init__(TestEngine(), run_base_dir,max_concurrent_jobs, poll_interval)
        self.model_include_patterns = None
        self.model_ignore_patterns.extend([])
        script_dir = Path(__file__).parent.resolve()
        self.run_base_dir = script_dir / "../data/"
        shutil.rmtree(self.run_base_dir, ignore_errors=True)
    

def main(args=None):
    import sys
    from argparse import ArgumentParser
    try:
        import Pyro5.api
        defaultPyroDispatchHost = "localhost"
        defaultPyroDispatchPort = 44444
        defaultPyroDispatchName = "ProxyDispatch"

        Pyro5.api.config.PICKLE_ENABLE = False
    except ImportError:
        print(
            "Error: 'Pyro5' is required to launch the dispatch daemon CLI.\n"
            "Please install it using: pip install Pyro5 (or pip install .[pyro])",
            file=sys.stderr
        )
        sys.exit(1)
    
    parser = ArgumentParser(description="D-Manage proxy dispatch command line launcher.")
    parser.add_argument("-n", "--host", dest="host", default=defaultPyroDispatchHost, help="hostname to bind server on")
    parser.add_argument("-p", "--port", dest="port", type=int, default=defaultPyroDispatchPort, help="port to bind server on (0=random)")
    options = parser.parse_args(args)

    Pyro5.api.serve(
        {TestDispatcher: defaultPyroDispatchName},
        host=options.host,
        port=options.port,
        use_ns=False
    )

if __name__ == "__main__":
    main()