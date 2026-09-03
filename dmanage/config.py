from typing import Literal

PARALLEL_BACKEND: Literal["multiprocessing", "multiprocess", "pickle", "dill"] = "multiprocessing"
"""The execution backend for parallel operations.

Supported options:

* ``'multiprocessing'`` or ``'pickle'``: Standard library multiprocessing.
* ``'multiprocess'`` or ``'dill'``: Extended serialization using ``dill``.
"""
