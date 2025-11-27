# -*- coding: utf-8 -*-


class add_attribute:
    """Decorator that adds an attribute to a function without wrapping or renaming it."""
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __call__(self, func):
        setattr(func, self.name, self.value)
        return func

def override(kind='default',level=None):
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
        return add_attr(func)
    return _override


if __name__ == "__main__":
    # @add_attribute('_override',True)
    # def test():
    #     pass

    @override()
    def test():
        pass


    print(test)
    print(test._override)
    pass