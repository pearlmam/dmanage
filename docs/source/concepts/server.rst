Server Interface
================

There are three ways to interface with data objects on a server. 

Remote Desktop/ssh
------------------

This is the simplest and most common way to interface with a server. You synchronize your project onto the server, and interact with your code through ssh or remote desktop. The advantage is simplicity and full access to the server. The disadvantage is network speed makes the user interface laggy and no inherent script or data synchronization between client, server, and other servers. Processing data on the server cannot be automated and compared with data on another server without micromanaging everything. This is the motivation for the RPC and Paramiko interfaces.

Remote Protocol Computing (RPC)
-------------------------------

RPC allows access to objects on the server as if they were local to the client. This is achieved by running a instance of an object on the server and accessing it through a proxy on the client. In D-Manage, an instance of your data object is created on the server, you can call its methods from your client, and return results to your client directly. The convenience of this cannot be overstated. And this sets up the framework for data visualization on the server.

Paramiko
--------

Paramiko is the python equivalent of ssh and sftp. For running remote commands, this package is ideal. For interacting with Python objects, not so much.

This method basically transfers a script to run on the server. This method is relatively simple, but a pain to actually do. You synchronize the project on the server, along with the run script, Paramiko runs a terminal command to run the script on the server, and results either can either be returned to the client through terminal output (a pain in the neck), or written to a file to be retrieved by the client. This requires micromanaging multiple files, server environments, has high startup overhead, and debugging is difficult. 



