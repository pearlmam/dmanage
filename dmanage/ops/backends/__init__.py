import importlib
from dmanage._compat import HAS_PANDAS, HAS_POLARS

# Auto-detect available engine
if HAS_PANDAS:
    _DEFAULT_BACKEND = "pandas"
elif HAS_POLARS:
    _DEFAULT_BACKEND = "polars"
else:
    _DEFAULT_BACKEND = None

def get_backend(name=None):
    target = name or _DEFAULT_BACKEND
    if not target:
        raise RuntimeError("No supported DataFrame backend (pandas/polars) is installed.")
    return importlib.import_module(f"dmanage.ops.backends.{target}")