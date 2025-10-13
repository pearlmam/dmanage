#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  7 16:45:33 2025

@author: marcus
"""
import inspect
import types

# component classes
class A():
    def func(self):
        return'A'
    
class B():
    def func(self):
        return 'B'
    
#########################################
#    object approach
#########################################

# composite parent class
class C1():
    def __init__(self):
        self.A = A()
        self.B = B()
        self._original_methods = {}  # Store backups here
        self._apply_component_overrides()
    def func(self):
        return 'C'
    
    def _apply_component_overrides(self):
        for attr_name in dir(self):
            if "_" not in attr_name:
                continue

            prefix, _, func_name = attr_name.partition("_")
            component = getattr(self, prefix, None)
            if not component or not hasattr(component, func_name):
                continue

            override_func = getattr(self, attr_name)
            original_func = getattr(component, func_name)

            # Save the original for later reference
            self._original_methods[f"{prefix}.{func_name}"] = original_func

            # Bind a wrapper that can call the original method
            def make_wrapper(override_func, original_func):
                def wrapper(*args, **kwargs):
                    # Attach original method to override_func.supercall
                    return override_func(original_func, *args, **kwargs)
                return wrapper

            setattr(component, func_name, make_wrapper(override_func, original_func))

# composite subclass 
class D1(C1):
    def __init__(self):
        super().__init__()
    def func(self):
        return 'D' + super().func()  # returns 'DC'
    
    # overwrite A.func() and B.func()  manually
    def A_func(self,original):
        return 'D' + original()   # returns 'DA'
    def B_func(self,original):
        return 'D' + original   # returns 'DA'





#########################################
#    decorator approach
#########################################
def component_override(component_name, method_name):
    """Decorator to mark a method as an override for a component method."""
    def decorator(func):
        func._component_override = (component_name, method_name)
        return func
    return decorator

# composite parent class
class C2():
    def __init__(self):
        self.A = A()
        self.B = B()
        self._original_methods = {}  # Store backups here
        self._apply_component_overrides()
    def func(self):
        return 'C'
    
    def _apply_component_overrides(self):
        """Attach decorated override methods to their corresponding components."""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "_component_override"):
                component_name, method_name = method._component_override
                component = getattr(self, component_name, None)
                if not component or not hasattr(component, method_name):
                    continue

                original_func = getattr(component, method_name)
                self._original_methods[f"{component_name}.{method_name}"] = original_func

                # Build wrapper that passes original function to override
                def make_wrapper(override_method, original_func):
                    def wrapper(*args, **kwargs):
                        return override_method(original_func, *args, **kwargs)
                    return wrapper

                setattr(component, method_name, make_wrapper(method, original_func))
                
# composite subclass 
class D2(C2):
    def __init__(self):
        super().__init__()
    def func(self):
        return 'D' + super().func()  # returns 'DC'
    
    @component_override("A", "func")
    def A_func(self,original):
        return 'D' + original()   # returns 'DA'
    
    @component_override("B", "func")
    def B_func(self,original):
        return 'D' + original   # returns 'DA'

#########################################
#    Fallbacks approach
#########################################

def component_override(component_name, method_name):
    """Decorator to mark a method as an override for a component method."""
    def decorator(func):
        func._component_override = (component_name, method_name)
        return func
    return decorator

# composite parent class
class C3():
    def __init__(self):
        self.A = A()
        self.B = B()
        self._original_methods = {}  # Store backups here
        self._apply_component_overrides()
    def func(self):
        return 'C'
    
    def _apply_component_overrides(self):
        """Attach decorated override methods to their corresponding components."""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if not hasattr(method, "_component_override"):
                continue

            component_name, method_name = method._component_override
            component = getattr(self, component_name, None)

            # --- fallback if component not found ---
            if component is None:
                print(f"[⚠️] Component '{component_name}' not found on {self.__class__.__name__}, skipping.")
                continue

            # --- fallback if target method not found ---
            original_func = getattr(component, method_name, None)
            if original_func is None:
                print(f"[⚠️] Method '{component_name}.{method_name}()' not found. Using fallback.")
                def original_func(*args, **kwargs):
                    print(f"[ℹ️] Fallback called for missing {component_name}.{method_name}()")
                    return None

            self._original_methods[f"{component_name}.{method_name}"] = original_func

            # Wrap so override gets original
            def make_wrapper(override_method, original_func):
                def wrapper(*args, **kwargs):
                    try:
                        return override_method(original_func, *args, **kwargs)
                    except Exception as e:
                        print(f"[❌] Error in override {override_method.__name__}: {e}")
                return wrapper

            setattr(component, method_name, make_wrapper(method, original_func))
            print(f"[✅] Overrode {component_name}.{method_name}() with {self.__class__.__name__}.{method.__name__}()")

                
# composite subclass 
class D3(C3):
    def __init__(self):
        super().__init__()
    def func(self):
        return 'D' + super().func()  # returns 'DC'
    
    @component_override("A", "func")
    def A_func(self,original):
        return 'D' + original()   # returns 'DA'
    
    @component_override("B", "func")
    def B_func(self,original):
        return 'D' + original   # returns 'DA'



#########################################
#    Automated approach
#########################################
def component_override(label):
    """Decorator to mark a method as an override for a component method."""
    def decorator(func):
        func._component_override = label
        return func
    return decorator


# component classes
class A():
    @component_override('override')
    def func(self):
        #setattr(A.func, '_component_override', 'override')
        #self.func._component_override = 
        return'A'
    
class B():
    def func(self):
        return 'B'
    
# composite parent class
class C4():
    def __init__(self):
        self.A = A()
        self.B = B()
        self._original_methods = {}  # Store backups here
        self._wrap_component_methods()
        
    def func(self):
        return 'C'
    
    def _wrap_component_methods(self):
        """Scan all attributes and wrap methods of component-like objects."""
        for attr_name, attr_value in vars(self).items():
            if attr_name.startswith("_"):
                continue  # skip internal attributes
            if not hasattr(attr_value, "__class__"):
                continue  # skip primitives

            # Detect component-like objects (skip classes, numbers, etc.)
            if inspect.isclass(attr_value) or isinstance(attr_value, (int, float, str, dict, list, tuple)):
                continue

            # Wrap all public methods of the component
            for method_name, method in inspect.getmembers(attr_value, predicate=inspect.isroutine):
                if method_name.startswith("_"):
                    continue  # skip private methods
                elif not hasattr(method, "_component_override"):
                    continue  # skip methods without '_component_override' attribute
                original_func = method
                wrapped = self._make_wrapper(attr_name, method_name, original_func)
                setattr(attr_value, method_name, types.MethodType(wrapped, attr_value))
                self._original_methods[f"{attr_name}.{method_name}"] = original_func

    def _make_wrapper(self, component_name, method_name, original_func):
        def wrapper(_self, *args, **kwargs):
            # If subclass defines on_component_call, use it
            if hasattr(self, "on_component_call"):
                return self.on_component_call(
                    component_name,
                    method_name,
                    lambda *a, **kw: original_func(*a, **kw),
                    *args,
                    **kwargs,
                )
            else:
                return original_func(*args, **kwargs)
        return wrapper
                
# composite subclass 
class D4(C4):
    def __init__(self):
        super().__init__()
    def func(self):
        return 'D' + super().func()  # returns 'DC'
    
    def on_component_call(self, component_name, method_name, original, *args, **kwargs):
        return 'D' + original(*args, **kwargs)   # returns 'DA'

#########################################
#    Automated approach but wrapping in subclass
#########################################
def component_override(label):
    """Decorator to mark a method as an override for a component method."""
    def decorator(func):
        func._component_override = label
        return func
    return decorator


# component classes
class A():
    @component_override('override')
    def func(self):
        #setattr(A.func, '_component_override', 'override')
        #self.func._component_override = 
        return'A'
    
class B():
    def func(self):
        return 'B'
    
# composite parent class
class C5():
    def __init__(self):
        self.A = A()
        self.B = B()
        
    def func(self):
        return 'C'
                  
# composite subclass 
class D5(C5):
    def __init__(self):
        super().__init__()
        # self._original_methods = {}  # Store backups here, not needed
        self._wrap_component_methods()
    def func(self):
        return 'D' + super().func()  # returns 'DC'
    
    def _wrap_component_methods(self):
        """Scan all attributes and wrap methods of component-like objects."""
        for attr_name, attr_value in vars(self).items():
            if attr_name.startswith("_"):
                continue  # skip internal attributes
            if not hasattr(attr_value, "__class__"):
                continue  # skip primitives

            # Detect component-like objects (skip classes, numbers, etc.)
            if inspect.isclass(attr_value) or isinstance(attr_value, (int, float, str, dict, list, tuple)):
                continue

            # Wrap all public methods of the component
            for method_name, method in inspect.getmembers(attr_value, predicate=inspect.isroutine):
                if method_name.startswith("_"):
                    continue  # skip private methods
                elif not hasattr(method, "_component_override"):
                    continue  # skip methods without '_component_override' attribute
                original_func = method
                wrapped = self._make_wrapper(attr_name, method_name, original_func)
                setattr(attr_value, method_name, types.MethodType(wrapped, attr_value))
                #self._original_methods[f"{attr_name}.{method_name}"] = original_func

    def _make_wrapper(self, component_name, method_name, original_func):
        def wrapper(_self, *args, **kwargs):
            # If subclass defines on_component_call, use it
            if hasattr(self, "on_component_call"):
                return self.on_component_call(
                    component_name,
                    method_name,
                    lambda *a, **kw: original_func(*a, **kw),
                    *args,
                    **kwargs,
                )
            else:
                return original_func(*args, **kwargs)
        return wrapper

    def on_component_call(self, component_name, method_name, original, *args, **kwargs):
        print(f"⚡ Before {component_name}.{method_name}")
        result = original(*args, **kwargs)
        print(f"✅ After {component_name}.{method_name}")
        return result
    
    
    def on_component_call(self, component_name, method_name, original, *args, **kwargs):
        return 'D' + original(*args, **kwargs)   # returns 'DA'

objC1 = C1()
objC1.A.func()        
objD5 = D5()  
print(objD5.A.func())  

  
