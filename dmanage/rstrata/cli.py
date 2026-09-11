# -*- coding: utf-8 -*-
from pathlib import Path
import Pyro5.api
from dmanage.rstrata import PyroFactory
from argparse import ArgumentParser


__all__ = ["main"]
defaultPyroFactoryHost = "127.0.0.1"
defaultPyroFactoryPort = 44444
defaultPyroFactoryName = "ProxyFactory"
script_dir = Path(__file__).parent.resolve()
rel_dir = Path("../../tests/helpers")
TEST_CONFIG_PATH = script_dir / rel_dir / "rpc_config.py"
TEST_PICKLE_CONFIG_PATH = script_dir / rel_dir / "rpc_config_pickle.py"

def main(args=None):
    parser = ArgumentParser(description="D-Manage proxy factory command line launcher.")
    parser.add_argument("-n", "--host", dest="host", default="127.0.0.1")
    parser.add_argument("-p", "--port", dest="port", type=int, default=defaultPyroFactoryPort)
    parser.add_argument("-c", "--config", dest="config", default=False)
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--test-pickle", action="store_true")
    parser.add_argument("-b", "--parallel-backend", choices=["multiprocessing", "multiprocess"], default=None)

    options = parser.parse_args(args)
    if not (options.test or options.config):
        parser.error("argument -c/--config is required unless --test is set.")

    config_path = (
        TEST_PICKLE_CONFIG_PATH if options.test_pickle else TEST_CONFIG_PATH
    ) if options.test else options.config

    pyroFactory = PyroFactory(
        configPath=config_path, parallel_backend=options.parallel_backend
    )
    Pyro5.api.serve(
        {pyroFactory: defaultPyroFactoryName},
        host=options.host,
        port=options.port,
        use_ns=False,
    )


if __name__ == "__main__":
    main()