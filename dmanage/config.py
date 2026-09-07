from typing import Literal,Optional

__all__ = ["PARALLEL_BACKEND", "PARALLEL_START_METHOD"]

PARALLEL_BACKEND: Literal["multiprocessing", "multiprocess", "pickle", "dill"] = "multiprocessing"
"""The execution backend for parallel operations.

Supported options:

* ``'multiprocessing'`` or ``'pickle'``: Standard library multiprocessing.
* ``'multiprocess'`` or ``'dill'``: Extended serialization using ``dill``.
"""

PARALLEL_START_METHOD: Optional[Literal["fork", "spawn", "forkserver"]] = None
"""The process creation method for worker pools.

Supported options:
* ``'fork'``: Fast, low-overhead process cloning (POSIX default prior to Python 3.14).
* ``'spawn'``: Fresh interpreter start; safer across C-extensions, required on Windows.
* ``'forkserver'``: Balanced worker server launch (Python 3.14+ Linux default).
* ``None``: Fall back to Python's system default for the active backend.
"""