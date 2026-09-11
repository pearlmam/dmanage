# -*- coding: utf-8 -*-
try:
    import Pyro5.api
except ImportError:
    raise ImportError(
        "Module 'Pyro5' must be installed to use the rpc package. Use "
        "'pip install dmanage[Pyro5]' or 'pip install dmanage[Pyro5-with-pickle]'"
    )

from . import _serializers  # Registers all Pyro/Pandas/URI hooks once on main thread
from ._client import ProxyFactory, ProxyWrap, client_ssh_setup, client_ssh_close
from ._server import PyroFactory, start_factory
from ._utils import Pyroize


from ._client import __all__ as _client_all
from ._server import __all__ as _server_all
from ._utils import __all__ as _utils_all

__all__ = _client_all + _server_all + _utils_all


# Friendly public aliases
connect = ProxyFactory
serve = start_factory

__all__ = [
    "connect",
    "serve",
    "ProxyFactory",
    "ProxyWrap",
    "PyroFactory",
    "Pyroize",
    "start_factory",
    "client_ssh_setup",
    "client_ssh_close",
]