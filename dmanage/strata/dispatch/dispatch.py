# -*- coding: utf-8 -*-

from dmanage.remote import rpc

# maybe split into a "run" class and a "sweep" class?


class Dispatch():
    
    def __init__(self):
        pass
    
    def setup_env(self,):
        """setup environment
        
        python environment
        simulation config
        simulation commands
        
        """
        pass
    
    # run stuff
    def setup_run(self):
        pass
    
    def start_run(self):
        pass
    
    def stop_run(self):
        pass
    
    def get_active_runs(self):
        pass
    
    def get_run_progress(self):
        pass
    
    
    # sweep stuff
    def setup_sweep(self):
        pass
    
    def start_sweep(self):
        pass
    
    def stop_sweep(self):
        pass
    
    def get_active_sweeps(self):
        pass
    
    def remove_run_from_sweep(self):
        pass
    
    def get_sweep_progress(self):
        pass
    
    
    
    