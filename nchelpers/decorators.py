from functools import wraps
from threading import local


def prevent_infinite_recursion(func):
    """Decorator that detects infinite recursion of a function and raises an
    exception if so.
    Adopted from http://stackoverflow.com/a/15955706.
    Thread-safe. Function arguments must be hashable.
    """
    func._thread_locals = local()

    @wraps(func)
    def wrapper(*args, **kwargs):
        params = tuple(args) + tuple(kwargs.items())

        if not hasattr(func._thread_locals, 'seen'):
            func._thread_locals.seen = set()
        if params in func._thread_locals.seen:
            raise RuntimeError(
                'Already called {} with the same arguments'
                .format(func.__name__))

        func._thread_locals.seen.add(params)
        try:
            res = func(*args, **kwargs)
        finally:
            func._thread_locals.seen.remove(params)

        return res

    return wrapper
