# Asynction
[![Tests Status](https://github.com/dedoussis/asynction/workflows/tests/badge.svg)](https://github.com/dedoussis/asynction/actions?query=workflow%3Atests)

SocketIO python framework driven by the [AsyncAPI](https://www.asyncapi.com/) specification. Built on top of [Flask-SocketIO](https://github.com/miguelgrinberg/Flask-SocketIO). Inspired by [Connexion](https://github.com/zalando/connexion).

The purpose of Asynction is to empower a specification first approach when developing [SocketIO](https://socket.io/) APIs in Python.

*Disclaimer: Asynction is still at a very early stage and should not be used in production codebases.*

## Prerequisites
* Python 3.7 (or higher)

## Install
```bash
$ pip install asynction
```

## Usage
Example event and error handler callables sitting under `./my_api/handlers.py`:
```python
def user_signedup():
    logger.info("Registered user")

def user_error(e):
    logger.error("Error: %s", e)
```

Example specification sitting under `./docs/asyncapi.yaml`:
```yaml
asyncapi: 2.0.0
info:
  title: Account Service
  version: 1.0.0
  description: This service is in charge of processing user signups
channels:
  user/signedup:  # A namespace can be specified by prefixing the channel name
    publish:
      operationId: my_api.handlers.user_signedup
      message:
        $ref: '#/components/messages/UserSignedUp'
components:
  messages:
    UserSignedUp:
      payload:
        type: object
x-namespaces:
  /user:
    description: Special namespace that only registered users have access to
    errorHandler: my_api.handlers.user_error
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
The above `asio` server object has all the event and error handlers registered, and is ready to run.
Without Asynction, one would need to add additional boilerplate to register the handlers (as shown [here](https://flask-socketio.readthedocs.io/en/latest/#error-handling)).

## Specification Extentions (support for SocketIO Namespaces)
Asynction has extended the AsyncAPI 2.0.0 specification to provide support for the [Namespaces](https://socket.io/docs/v4/namespaces/) concept of the SocketIO protocol. The extentions introduced adhere to the [Specification Extention guidelines](https://www.asyncapi.com/docs/specifications/2.0.0#specificationExtensions) of the AsyncAPI spec.

### Namespace definition (object)
An `x-namespaces` field has been defined as a top level key of the [AsyncAPI](https://www.asyncapi.com/docs/specifications/2.0.0#A2SObject) object. The value of this field is a Namespace Definitions Object. The Namespace Definitions Object is a map object (with patterned fields).

#### Namespace Definitions Object
| Field Pattern                           | Type                                          | Description                                                                                                                                                                                            |
|-----------------------------------------|-----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `^[A-Za-z0-9_\-]+/$` | [Namespace Item Object](#namespace-item-object) | Each key must correspond to a namespace supported by the SocketIO server. Each value is a [Namespace Item Object](#namespace-item-object), providing the definition of that namespace. |

#### Namespace Item Object
| Field Name   | Type     | Description                                         |
|--------------|----------|-----------------------------------------------------|
| description  | `string` | An optional description of this namespace           |
| errorHandler | `string` | Dot joint path to the python error handler callable |

### Event handler namespacing (semantic)
A new semantic added to the AsyncAPI 2.0.0 spec is the prefixing of the channel paths (keys of the [Channels Object](https://www.asyncapi.com/docs/specifications/2.0.0#channelsObject)). This allows the registration of an event handler under a particular namespace. The prefix expressed namespace should be included in the [Namespace Definitions Object](#namespace-definitions-object). 

The pattern of the channel path is: `^(?<namespace>[A-Za-z0-9_\-]+/)?(?<channel_name>[A-Za-z0-9_\-/]+)$`

If the namespace prefix is omitted, the main namespaced (`/`) is assumed.

## TODOs
1. Payload validation
2. Increase JSON Schema reference resolution test coverage. Allow refs to be used with other keys. Merge upon ref resolution.
3. Authentication
