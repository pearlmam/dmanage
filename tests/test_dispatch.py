# -*- coding: utf-8 -*-

from tests.helpers.dispatch_object import TestDispatcher
from pathlib import Path
try:
    import Pyro5.api
except ImportError:
    # No-op decorator if Pyro5 is not installed
    pass

host= '127.0.0.1'
port = 44444
script_dir = Path(__file__)
model_path = script_dir / "helpers/dispatch_model/dispatch_model.py"

job_parameters = [{'var0':1.0, 'var1':2.0},
                  {'var0':1.0, 'var1':3.0}]



def test_dispatch(self):
    """Make sure factor is running with terminal command 'dmanage-factory'"""
    uri = "PYRO:ProxyDispatch@localhost:44444"
    dispatchProxy =  Pyro5.api.Proxy(uri=uri)
    dispatchProxy.create_job()
    
if __name__ == "__main__":
    uri = "PYRO:ProxyDispatch@localhost:44444"
    # dispatch =  Pyro5.api.Proxy(uri=uri)
    
    dispatch = TestDispatcher()
    dispatch.set_poll_interval(1.0)
    for job_parameter in job_parameters:
        job_info_local = dispatch.create_job(model_path, job_params=job_parameter,nc=1)
    jobs = dispatch.get_jobs()
    job_ids = dispatch.get_ids()
    dispatch.submit_pending()
    # jobs = dispatch.get_jobs()
    # dispatch.kill_active_jobs()
    # dispatch.stop_scheduler()
    
    
    