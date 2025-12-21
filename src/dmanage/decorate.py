# -*- coding: utf-8 -*-


class add_attribute:
    """Decorator that adds an attribute to a function without wrapping or renaming it.
    To Do: make it so you can add more attrs at once or over multiple calls
    """
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def __call__(self, func):
        setattr(func, self.name, self.value)
        return func

def override(kind='default',level=None,**kwargs):
    """
    

    Parameters
    ----------
    kind : string, optional
        This is the value of the _override attribute. This chooses which kind of 
        override to apply. The default is 'default'.
    level : int, optional
        NOT IMPLEMENTED. This will choose which level to apply the override.
        The default is None.

    Returns
    -------
    function
        This is the same function to be decorated but with an added _override attribute
        with kind as the value.

    """
    
    def _override(func):
        """Decorator to add an override attribute for a method."""
        add_attr = add_attribute('_override',kind)
        func = add_attr(func)
        add_attr = add_attribute('_level',level)
        func = add_attr(func)
        add_attr = add_attribute('_kwargs',kwargs)
        func = add_attr(func)
        return func
    return _override


if __name__ == "__main__":
    # @add_attribute('_override',True)
    # def test():
    #     pass

    @override('hi',a=1,b=2)
    def test():
        pass


    print(test)
    print(test._override)
    print(test._level)
    print(test._args)
    
    pass