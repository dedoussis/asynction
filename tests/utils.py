from typing import Callable


def deep_unwrap(func: Callable, depth: int = -1) -> Callable:
    """
    Unwrap a callable that has been wrapped multiple times with functools.wraps
    """
    if hasattr(func, "__wrapped__") and depth != 0:
        return deep_unwrap(getattr(func, "__wrapped__"), depth - 1)

    return func
