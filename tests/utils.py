from typing import Callable


def deep_wrapped(func: Callable) -> Callable:
    if hasattr(func, "__wrapped__"):
        return deep_wrapped(getattr(func, "__wrapped__"))

    return func
