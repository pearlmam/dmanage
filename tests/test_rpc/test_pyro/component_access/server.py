# -*- coding: utf-8 -*-
import Pyro5.api
#import inspect

@Pyro5.api.expose
class ExposeComps:
    """The functions here allow automatic proxy creation for component classes"""
    def __exposed_comps__(self):
        """This allows reading from _exposedComps attribute over a Proxy """
        return  getattr(self,'_exposedComps',[])
    
    def __get_comp_proxy__(self,name):
        """Creates a shared object from the component and returns the uri"""
        Comp = getattr(self,name)
        self._pyroDaemon.register(Comp)   # autoproxy!
        return Comp

@Pyro5.api.expose
class Component1(ExposeComps):
    def __init__(self,name):
        self.name = name
        self.Comp = Component2('Component2 of Component1')
        self._exposedComps = ['Comp']
    def func(self):
        return self.name
      
@Pyro5.api.expose    
class Component2(Component1,ExposeComps):
    def __init__(self,name):
        self.name = name
        self._exposedComps = []

@Pyro5.api.expose    
class MyClass(ExposeComps):

    def __init__(self):
        self.attr = "attribute 'init def'"
        self.Comp = Component1('Component 1')
        self._exposedComps = ['Comp']
    
    def func(self):
        return "regular func"
           
if __name__ == "__main__":  
    port = 44444
    host = 'localhost'
    name = 'MyClass'
    Pyro5.api.serve({MyClass: name},host=host,port=port, use_ns=False)



