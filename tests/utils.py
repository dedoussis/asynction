from pathlib import Path
from typing import Any
from typing import Callable
from typing import Optional
from typing import Union

from flask import Flask
from flask_socketio import SocketIO
from typing_extensions import Protocol

from asynction.types import JSONMapping
from tests import fixtures


class AsynctionFactory(Protocol):
    def __call__(
        self,
        *args: Any,
        spec_path: Union[Path, JSONMapping] = fixtures.paths.simple,
        app: Optional[Flask] = None,
        **kwargs: Any
    ) -> SocketIO:
        ...


def deep_unwrap(func: Callable, depth: int = -1) -> Callable:
    """
    Unwrap a callable that has been wrapped multiple times with functools.wraps
    """
    if hasattr(func, "__wrapped__") and depth != 0:
        return deep_unwrap(getattr(func, "__wrapped__"), depth - 1)

    return func
