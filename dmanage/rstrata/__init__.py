# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
try:
    import Pyro5.api
except ImportError:
    raise ImportError(
        "Module 'Pyro5' must be installed to use the rpc package. Use "
        "'pip install dmanage[Pyro5]' or 'pip install dmanage[Pyro5-with-pickle]'"
    )

from . import serializers  # Registers all Pyro/Pandas/URI hooks once on main thread
from .client import ProxyFactory, ProxyWrap, client_ssh_setup, client_ssh_close
from .server import PyroFactory, start_factory
from .utils import Pyroize

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