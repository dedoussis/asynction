from flask_socketio import emit


def my_handler() -> None:
    # Dummy handler
    pass


def my_other_handler() -> None:
    # Dummy handler
    pass


def echo(message: str) -> None:
    emit("echo", message)
