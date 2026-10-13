
rstrata
-------

This module provides the framework for using your data objects remotely as if they were local. A data object factory daemon runs on the server which enables clients to create data object proxies to interact with data on the server. You setup an RPC factory on the server, instatiate the proxy factory on the client, and you can create data object proxies on the client to data objects on the server.

Server Setup
^^^^^^^^^^^^

First you setup an ``rpc_config.py`` file that defines the objects you want to expose; see example below.

.. literalinclude:: ../../../tests/helpers/rpc_config.py

Next you open a terminal and start the RPC factory.

.. code-block:: bash

    dmanage-factory --config path/to/rpc_config.py
    

Client Setup
^^^^^^^^^^^^

On the client, you just need to modify the script you use locally to use the proxy::

    import rstrata
    
    ### local implementation (commented out for remote use)
    # import MyDataGroup
    # datapath = "/path/to/local/data"
    # DG = MyDataGroup(datapath)
    
    # Remote implementation 
    datapath = "path/to/remote/data"  # path to the data on the remote machine
    
    ### setup Factory and create proxy
    host = "127.0.0.1"  # local loopback, should be your server address if not local
    port = 44444        # default port
    uri = f"PYRO:ProxyFactory@{host}:{port}"
    Factory = rstrata.ProxyFactory(uri=uri)
    DG = Factory.MyDataGroup(datapath) 
    
    ### process the data, remains the same whether local or remote
    result_1 = DG.my_awesome_method_1()
    result_2 = DG.my_awesome_method_2()
    ...
    

Caveats
^^^^^^^

Because the data is remote, method results should be small because of data transfer speeds over the network are slow. Also, the default serialization over RPC uses ``serpent`` which requires data to be python literals, no numpy, matplotlib, or other objects [#f1]_. To allow all datatypes, the Pyro5-with-pickle variant must be used and PICKLE_ENABLE must be set to true in your config file [#f2]_.

.. rubric:: Footnotes


.. [#f1] pandas DataFrames are allowed, but are converted to Dictionaries for transfer and may alter the data

.. [#f2] This is a MASSIVE security risk if other users have access to your server. See Pyro5-with-pickle documentation for more information on how to protect your system when using pickle. 

