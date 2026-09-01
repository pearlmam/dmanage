# -*- coding: utf-8 -*-

from importlib.metadata import entry_points

plugins = {}

def load():
    if plugins:   # already loaded
        return

    for ep in entry_points(group="dmanage.plugins"):
        register = ep.load()
        register(dmanage=__import__("dmanage"))
        
def get(name):
    load()
    return plugins[name]