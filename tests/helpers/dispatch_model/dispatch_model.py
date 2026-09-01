# -*- coding: utf-8 -*-

"""Test simulation model for the script"""
print("-----------------------------------------")
print("Script running\n")

import time
from dmanage.dispatch import load_job_config
var0 = 100
var1 = 100
time_sleep = 5
print(f"Variables before loading job config: \n    var0 = {var0}, var1 = {var1}\n")
load_job_config()
print(f"Variables after loading job config: \n    var0 = {var0}, var1 = {var1}\n")

print(f"Script calculations: sleep for {time_sleep} seconds...")
result = var0 + var1
time.sleep(time_sleep)

print("Script Finished")
print(f"result = {result}")
print("-----------------------------------------")