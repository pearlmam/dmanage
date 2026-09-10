# -*- coding: utf-8 -*-
from pathlib import Path
import importlib.util
import Pyro5.api

import dmanage.config
from .utils import expose_all, pyroize_object

defaultPyroFactoryHost = "127.0.0.1"
defaultPyroFactoryPort = 44444
defaultPyroFactoryName = "ProxyFactory"

script_dir = Path(__file__).parent.resolve()
rel_dir = Path("../../tests/helpers")
TEST_CONFIG_PATH = script_dir / rel_dir / "rpc_config.py"
TEST_PICKLE_CONFIG_PATH = script_dir / rel_dir / "rpc_config_pickle.py"


@Pyro5.api.expose
class PyroFactory:
    """
    Factory to create pyro objects on a remote machine to connect to as a proxy
    create an rpc configuration file to  load into this factory. This config file
    sets rpc options and lists the allowed objects this factory can create.
    ONLY objects in that list can be created. The most common objects for this are
    DataUnits and DataGroups, you can generate DUs and DGs on the server as if
    they were local. An example config file is below:
        ::
            import Pyro5
            import sys
            from pathlib import Path
            import dmanage.config
            sys.path.insert(0, str(Path(__file__).parent.resolve()))
            from strata_objects import Parent,MyDataGroup,MyDataUnit,MyNewDataGroup,MyNewDataUnit

            ONLY_EXPOSED = False
            Pyro5.api.config.PICKLE_ENABLE = False # Enabling pickle is a massive security risk
            Pyro5.api.config.SERIALIZER = "serpent"# serpent,json?,pickle,dill
            dmanage.config.PARALLEL_BACKEND = "multiprocessing" # This is the local serializer used in multiprocessing, safe!

            EXPOSED_OBJECTS = {
                "Parent":Parent,
                "MyDataGroup":MyDataGroup,
                "MyDataUnit":MyDataUnit,
                "MyNewDataGroup":MyNewDataGroup,
                "MyNewDataUnit":MyNewDataUnit,
                }
    
    """

    config_path = None

    def __init__(self, configPath=None, parallel_backend=None):
        self.configPath = Path(configPath)
        if not self.configPath.exists():
            raise FileNotFoundError(f"Config file not found: {self.configPath}")
        self._load_config()
        self._pyro_uris = {}
        self.set_parallel_backend(parallel_backend)

    def _load_config(self):
        spec = importlib.util.spec_from_file_location(
            "custom_rpc_config", self.configPath
        )
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        self._exposed_objects = getattr(config_module, "EXPOSED_OBJECTS", {})
        self.ONLY_EXPOSED = getattr(config_module, "ONLY_EXPOSED", False)

    def _get_object(self, name):
        if name not in self._exposed_objects:
            raise Exception(f"No object named '{name}' is exposed to this factory")
        return self._exposed_objects[name]

    def get_exposed_object_list(self):
        return list(self._exposed_objects.keys())

    def create(self, name, reload=False, args=(), kwargs={}):
        """
        reload can reuse uri or create new instance; however if a new instance 
        is created, the uri is no longer stored in self._pyro_uris. Pyro objects
        are cleaned up periodically when proxies are deleted... I think.
        """
        
        if name in self._pyro_uris and not reload:
            print(f"Object '{name}' already shared, 'reload=False': using cached uri")
            return self._pyro_uris[name]

        print(f"Creating pyro object: '{name}'...", end=" ")
        obj = self._get_object(name)
        if not self.ONLY_EXPOSED:
            obj = expose_all(obj)
        obj = pyroize_object(obj)
        obj = obj(*args, **kwargs)
        uri = str(self._pyroDaemon.register(obj, force=True, weak=False))
        print("Done")
        obj.__register_components__()

        self._pyro_uris[name] = uri
        return uri

    def set_parallel_backend(self, backend=None):
        if backend:
            dmanage.config.PARALLEL_BACKEND = backend
            print(f"Parallel backend changed to '{backend}'")

    def get_parallel_backend(self):
        return dmanage.config.PARALLEL_BACKEND

    def set_parallel_start_method(self, method=None):
        dmanage.config.PARALLEL_START_METHOD = method

    def get_parallel_start_method(self):
        return dmanage.config.PARALLEL_START_METHOD

    @classmethod
    def _create_instance(cls, *args, **kwargs):
        if cls.config_path is None:
            raise ValueError("Config path has not been set.")
        return cls(*args, **kwargs)


def start_factory(
    name="ProxyFactory", host="127.0.0.1", port=44444, loopCondition=lambda: True
):
    daemon = Pyro5.api.Daemon(host, port)
    with daemon:
        uri = daemon.register(PyroFactory, name)
        print(uri)
        daemon.requestLoop(loopCondition=loopCondition)


def main(args=None):
    from argparse import ArgumentParser

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