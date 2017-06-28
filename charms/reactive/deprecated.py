from functools import wraps
from inspect import getmodule


def alias(name):
    def _decorator(target):
        @wraps(target)
        def _alias(*args, **kwargs):
            return target(*args, **kwargs)
        _alias.__name__ = name
        _alias.__qualname__ = name
        _alias.__doc__ = "DEPRECATED Alias of `{}`.".format(target.__name__)
        setattr(getmodule(target), name, _alias)
        return target
    return _decorator
