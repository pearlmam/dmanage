# -*- coding: utf-8 -*-

import subprocess as sp

def check_active_procs(procName, procType=None):
    if procType == None:
        checkVorpalProc=sp.Popen('ps aux | grep ' + procName, shell=True, executable='/bin/bash', stdout=sp.PIPE, stderr=sp.PIPE)
    else:
        checkVorpalProc=sp.Popen('ps aux | grep ' + procType + ' | grep ' + procName, shell=True, executable='/bin/bash', stdout=sp.PIPE, stderr=sp.PIPE)

    output, err = checkVorpalProc.communicate()
    print(output)
    usedProcs = len(output.decode('ascii').split('\n'))-1
    return usedProcs