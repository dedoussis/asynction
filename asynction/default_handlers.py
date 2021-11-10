def default_on_connect_handler(*args, **kwargs):
    """Injected into api when security is specified by no connect handler is provided"""

    pass


DEFAULT_ON_CONNECT_HANDLER = "asynction.default_handlers.default_on_connect_handler"
