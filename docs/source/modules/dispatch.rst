
dispatch
--------

This module provides a pure python scheduler to submit simulation runs. The user creates their own ``engine`` class to run their specific simulation and ``dmanage.dispatch`` scheduler manages execution of the simulations. This scheduler is simple; however, there are more feature rich schedulers like the `Dask Scheduler`_ or `OpenPBS`_. The only advantage of the `dmanage.dispatch` scheduler is no extra packages are needed and it is simple; otherwise the other options are probably better.



.. _Dask Scheduler: https://docs.dask.org/en/stable/scheduler-overview.html
.. _OpenPBS: https://www.openpbs.org/


