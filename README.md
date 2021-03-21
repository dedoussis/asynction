# Asynction
[![Tests Status](https://github.com/dedoussis/asynction/workflows/tests/badge.svg)](https://github.com/dedoussis/asynction/actions?query=workflow%3Atests)

SocketIO python framework driven by the [AsyncAPI](https://www.asyncapi.com/) specification. Built on top of [Flask-SocketIO](https://github.com/miguelgrinberg/Flask-SocketIO). Inspired by [Connexion](https://github.com/zalando/connexion).

The purpose of `asynction` is to empower a specification first approach when developing [SocketIO](https://socket.io/) APIs in Python.

*Disclaimer: Asynction is still at a very early stage and should not be used in production codebases.*

## Prerequisites
* Python 3.7 (or higher)

## Install
```bash
$ pip install asynction
```

## Usage
Example event handler callable sitting under `./my_api/handlers.py`:
```python
def user_signedup():
    logger.info("Registered user")
```

Example specification sitting under `./docs/asyncapi.yaml`:
```yaml
asyncapi: 2.0.0
info:
  title: Account Service
  version: 1.0.0
  description: This service is in charge of processing user signups
channels:
  user/signedup:
    subscribe:
      operationId: my_api.handlers.user_signedup
      message:
        $ref: '#/components/messages/UserSignedUp'
components:
  messages:
    UserSignedUp:
      payload:
        type: object
```

Bootstrap the AsynctionSocketIO server:
```python
from asynction import AsynctionSocketIO
from flask import Flask

flask_app = Flask(__name__)

asio = AsynctionSocketIO.from_spec(
    spec_path="./docs/asyncapi",
    app=flask_app,
    message_queue="redis://",
    # any other kwarg that the flask_socketio.SocketIO constructor accepts
)
```
The `AsynctionSocketIO` class extends the `SocketIO` class of the Flask-SocketIO library.  
The above `asio` server object is ready be run without the need to register the event handlers.


## TODOs
1. `on_error` handlers
2. Increase JSON Schema reference resolution test coverage 
3. Payload validation
