from importlib import import_module
from typing import Callable
from typing import TypeVar


def load_handler(handler_id: str) -> Callable:
    *module_path_elements, object_name = handler_id.split(".")
    module = import_module(".".join(module_path_elements))

    return getattr(module, object_name)


T = TypeVar("T")
Func = Callable[..., T]
Decorator = Callable[[Func[T]], Func[T]]
