Server Interface
================

To be Developed


Seamlessly interfacing with a server is essential for data management. This makes processing data and debugging code on the server much easier and quicker. Often times scripts will run fine locally but fail on the server; debugging this is difficult and often requires a remote desktop on the server to debug the code locally. And then changing code on the server doesn't change your local code, so once you fix the bug, you have to make sure to copy those changes back to the local code and then debug the local implementation again. This is a nightmare.

RPC
---

We will use RPC for interactive use with a server. This starts a session on the server you can interact with in your local terminal. You can run local commands and run server commands. You can also transfer data from the server to the local workstation and vice versa.


Subprocess
----------

We will use use subprocess for submitting jobs that will run autonomously

This is arguably the most simple, but a pain to actually do. You send the project to the server, send a run script and then remotely run the script.
