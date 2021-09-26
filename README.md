# Asynction

[![Tests Status](https://github.com/dedoussis/asynction/workflows/tests/badge.svg)](https://github.com/dedoussis/asynction/actions/workflows/tests.yml) [![codecov](https://codecov.io/gh/dedoussis/asynction/branch/main/graph/badge.svg?token=3720QP2994)](https://codecov.io/gh/dedoussis/asynction) [![PyPI version](https://img.shields.io/pypi/v/asynction)](https://pypi.org/project/asynction/)

SocketIO python framework driven by the [AsyncAPI](https://www.asyncapi.com/) specification. Built on top of [Flask-SocketIO](https://github.com/miguelgrinberg/Flask-SocketIO). Inspired by [Connexion](https://github.com/zalando/connexion).

The purpose of Asynction is to empower a specification first approach when developing [SocketIO](https://socket.io/) APIs in Python. It guarantees that your API will work in accordance with its documentation.

_Disclaimer: Asynction is still at a beta stage. Extensive testing is recommended when using this library in production._

## Features

- Registers all event and error handlers that are referenced within the API specification.
- Provides out of the box validation on every Socket.IO interraction. In particular:
  - Event validation (for both ingress and egress events), based on the specified message schemata
  - HTTP request validation, upon connection, based on the channel binding schemata of each namespace
  - Callback validation, upon the ACK of a message, based on the message `x-ack` schemata
- Generates HTML rendered docs, similar to the AsyncAPI [playground](https://playground.asyncapi.io/?load=https://raw.githubusercontent.com/asyncapi/asyncapi/master/examples/2.0.0/simple.yml). The docs get served through the `GET {base_path}/docs` route of the app.
- [Mock server support](#mock-server)
- [CLI](#cli)
- Authentication à la [Connexion](https://connexion.readthedocs.io/en/latest/security.html) _(coming soon)_

A complete example can be found [here](example/) (includes examples of both normal and mock server implementations).

## Prerequisites

- Python 3.7 (or higher)

## Install

```console
$ pip install asynction
```

With mock server support:

```console
$ pip install asynction[mock]
```

With CLI support:

```console
$ pip install asynction[cli]
```

The CLI can also be installed via Homebrew:

```console
$ brew tap dedoussis/tap
$ brew install asynction
```

## Usage (basic example)

Example event and error handler callables located at `./my_api/handlers.py`:

```python
# /user namespace

def user_sign_up(data):
    logger.info("Signing up user...")
    emit("metrics", "signup", namespace="/admin", broadcast=True, callback=cb)

def user_log_in(data):
    logger.info("Logging in user...")
    emit("metrics", "login", namespace="/admin", broadcast=True, callback=cb)
    return True  # Ack

def user_error(e):
    logger.error("Error: %s", e)


# /admin namespace

def authenticated_connect():
    token = request.args["token"]

def admin_error(e):
    logger.error("Admin error: %s", e)
```

Example specification located at `./docs/asyncapi.yaml`:

```yaml
asyncapi: 2.1.0

info:
  title: User Account Service
  version: 1.0.0
  description: This service is in charge of processing user accounts

servers:
  production:
    url: my-company.com/api/socket.io # Customizes the `path` kwarg that is fed into the `SocketIO` constructor
    protocol: wss

channels:
  /user: # A channel is essentially a SocketIO namespace
    publish:
      message:
        oneOf: # The oneOf Messages relationship expresses the supported events that a client may emit under the `/user` namespace
          - $ref: "#/components/messages/UserSignUp"
          - $ref: "#/components/messages/UserLogIn"
    x-handlers: # Default namespace handlers (such as connect, disconnect and error)
      error: my_api.handlers.user_error # Equivelant of: `@socketio.on_error("/user")`
  /admin:
    subscribe:
      message:
        oneOf:
          - "#/components/messages/Metrics"
    x-handlers:
      connect: my_api.handlers.authenticated_connect # Equivelant of: `@socketio.on("connect", namespace="/admin")`
      error: my_api.handlers.admin_error
    bindings: # Bindings are used to validate the HTTP request upon connection
      $ref: "#/components/channelBindings/AuthenticatedWsBindings"

components:
  messages:
    UserSignUp:
      name: sign up # The SocketIO event name. Use `message` or `json` for unnamed events.
      payload: # Asynction uses payload JSON Schemata for message validation
        type: object
      x-handler: my_api.handlers.user_sign_up # The handler that is to be registered. Equivelant of: `@socketio.on("sign up", namespace="/user")`
    UserLogIn:
      name: log in
      payload:
        type: object
      x-handler: my_api.handlers.user_log_in
      x-ack: # Specifies the structure of the ACK data that the client should expect
        args:
          type: boolean
    Metrics:
      name: metrics
      payload:
        type: string
        enum: [signup, login]
      x-ack: # Specifies the structure of the ACK data that the server expects
        args:
          type: string

  channelBindings:
    AuthenticatedWsBindings:
      ws:
        query:
          type: object
          properties:
            token:
              type: string
          required: [token]
```

Bootstrap the AsynctionSocketIO server:

```python
from asynction import AsynctionSocketIO
from flask import Flask

flask_app = Flask(__name__)

asio = AsynctionSocketIO.from_spec(
    spec_path="./docs/asyncapi.yaml",
    app=flask_app,
    message_queue="redis://localhost:6379",
    # or any other kwarg that the flask_socketio.SocketIO constructor accepts
)

if __name__ == "__main__":
    asio.run(app=flask_app)
```

The `AsynctionSocketIO` class extends the `SocketIO` class of the Flask-SocketIO library.  
The above `asio` server object has all the event and error handlers registered, and is ready to run.  
Validation of the message payloads, the channel bindings and the ack callbacks is also enabled by default.  
Without Asynction, one would need to add additional boilerplate to register the handlers (as shown [here](https://flask-socketio.readthedocs.io/en/latest/#error-handling)) and implement the respective validators.

## Docs

API documentation is autogenerated by Asynction and served through the following routes of the app:

- `{base_path}/docs`: Rendered HTML docs similar to the AsyncAPI [playground](https://playground.asyncapi.io/?load=https://raw.githubusercontent.com/asyncapi/asyncapi/master/examples/2.0.0/simple.yml).
- `{base_path}/docs/asyncapi.json`: The raw specification data exposed for programmatic retrieval.

The `base_path` is determined automagically through the Socket.IO path argument. It essentially is the parent of that path. For example:

| Socket.IO path        | Base path | Docs path      |
| --------------------- | --------- | -------------- |
| `socket.io` (default) | `/`       | `/docs`        |
| `events/socket.io`    | `/events` | `/events/docs` |

Docs can be disabled by toggling the `docs` kwarg of the `AsynctionSocketIO.from_spec` factory method.

##  Mock server

Asynction can also create a fake "mock" based off an AsyncAPI document. This enables the consumers of a SocketIO API to interract with the API before it's even built.

```python
from asynction import MockAsynctionSocketIO
from flask import Flask

flask_app = Flask(__name__)

mock_asio = MockAsynctionSocketIO.from_spec(
    spec_path="./docs/asyncapi.yaml",
    app=flask_app,
)

if __name__ == "__main__":
    mock_asio.run(app=flask_app)
```

The mock server:

1. Listens for all events defined in the given spec, returning fake acknowledgements where applicable.
1. Periodically emits events containing payloads of fake data, for the clients to listen on.

The fake data generation is fueled by [Faker](https://faker.readthedocs.io/en/master/) and [Hypothesis](https://hypothesis.readthedocs.io/en/latest/), hence the use of the mock server functionality requires the installation of extra dependecies: `pip install asynction[mock]`

To make the fake generated data more realistic, one may attach faker providers to the string schemata of their spec using the [format](https://json-schema.org/understanding-json-schema/reference/string.html#format) keyword of JSON Schema:

```yaml
# example of a Message object
NewMessageReceived:
  name: new message
  payload:
    type: object
    properties:
      username:
        type: string
        format: first_name
      message:
        type: string
        format: sentence
    required: [username, message]
```

The formats supported are essentially all the [faker providers](https://faker.readthedocs.io/en/master/providers.html) that yield a string value.

## CLI

For convenience, Asynction provides a command-line interface (CLI) that aims to be a toolbox of useful utilities for the development, testing and mocking of Asynction apps (ie any Socket.IO app driven by an AsyncAPI doc). For example, it allows one to run a "mock" instance of their Socket.IO server, only by passing the AsyncAPI YAML file, without even having to start the development of the server itself.

All commands support the `–-help` (or `-h`) argument to display additional information.

### Available commands

- `mock run`

  ```console
  $ asynction --spec ./docs/asyncapi.yml mock run --port 5001 --debugger
  * Restarting with stat
  * Debugger is active!
  * Debugger PIN: 339-844-897
  (71320) wsgi starting up on http://0.0.0.0:5001
  ...
  ```

- `scaffold` _(coming soon)_

  ```console
  $ asynction --spec ./docs/asyncapi.yml scaffold
  ✨ Successfully generated app.py
  ```

### Dockerised

The CLI can be installed via pip or Homebrew (see the [install section](#install)) but is also available through docker, negating the need for a local python environment:

```console
$ docker run -v ${PWD}/docs/asyncapi.yml:/opt/asynction/asyncapi.yml dedoussis/asynction mock run --debugger
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 339-844-897
(71320) wsgi starting up on http://0.0.0.0:5000
...
```

## Further resources

- [API reference](https://asynction.dedouss.is)
- [Complete example](example/)

## Specification Extentions

Asynction has extended the AsyncAPI 2.x.x specification to provide support for coupling SocketIO semantical entities (such as namespaces, events and acks) to python objects (such as handler callabes or other `flask_socketio.SocketIO` methods). Some of the extentions below are necessary to express the Socket.IO protocol semantics, while others are solely needed for the programmatic purposes of Asynction. The extentions introduced adhere to the [Specification Extention guidelines](https://www.asyncapi.com/docs/specifications/2.0.0#specificationExtensions) of the AsyncAPI spec.

For further guidance on how to generally express a SocketIO API using AsyncAPI, refer to this article: <https://dedouss.is/posts/2021-07-14-documenting-socketio-part-2.html>

### Event handler

The `x-handler` field MAY be defined as an additional property of the [Message Object](https://www.asyncapi.com/docs/specifications/2.0.0#messageObject). The value of this field MUST be of `string` type, expressing a dot joint path to a python callable (the event handler).

Message Objects listed under a `subscribe` [operation](https://www.asyncapi.com/docs/specifications/2.0.0#operationObject) MUST include the `x-handler` field.  
Message Objects listed under a `publish` [operation](https://www.asyncapi.com/docs/specifications/2.0.0#operationObject) SHOULD NOT include the `x-handler` field.

### Default namespace handlers

The `x-handlers` field MAY be defined as an additional property of the [Channel Item Object](https://www.asyncapi.com/docs/specifications/2.0.0#channelItemObject). The value of this field SHOULD be a [Channel Handlers Object](#channel-handlers-object).

#### Channel Handlers Object

| Field Name | Type     | Description                                              |
| ---------- | -------- | -------------------------------------------------------- |
| connect    | `string` | Dot joint path to the python connect handler callable    |
| disconnect | `string` | Dot joint path to the python disconnect handler callable |
| error      | `string` | Dot joint path to the python error handler callable      |

### ACK packet

The basic unit of information in the [Socket.IO protocol](https://github.com/socketio/socket.io-protocol) is the packet. There are 7 distinct [packet types](https://github.com/socketio/socket.io-protocol#packet-types). The `publish` and `subscribe` [Message Object](https://www.asyncapi.com/docs/specifications/2.0.0#messageObject)s expressed in the A2S YAML above correspond to the [EVENT](https://github.com/socketio/socket.io-protocol#2---event) and [BINARY_EVENT](https://github.com/socketio/socket.io-protocol#5---binary_event) packet types. These are essentially the packets that are transmitted when the Socket.IO sender invokes the `emit` or `send` API functions of the Socket.IO library (regardless of implementation). In turn, the Socket.IO event receiver handles the received event using the `on` API function of the Socket.IO library. As part of the `on` handler, the receiver may choose to return an acknowledgement of the received message. This acknowledgement is conveyed back to the transmitter via the [ACK](https://github.com/socketio/socket.io-protocol#3---ack) and [BINARY_ACK](https://github.com/socketio/socket.io-protocol#5---binary_event) packet types. This ack data is passed as input into the callback that the message transmitter has provided through the `emit`/`send` invocation.

In order to express the above acknowledgement semantics, the A2S specification needs to be extended as follows:

- [Message Object](https://www.asyncapi.com/docs/specifications/2.0.0#messageObject)s MAY include the `x-ack` field. The value of this field SHOULD be a [Message Ack Object](#message-ack-object).
- [Components Object](https://www.asyncapi.com/docs/specifications/2.0.0#componentsObject) MAY include the `x-messageAcks` field. The value of this field should be of type: `Map[string, Message Ack Object | Reference Object]`

Although Asynction uses these fields to validate the input args of the callback functions, these ACK extentions are necessary to express semantics of the [Socket.IO protocol](https://github.com/socketio/socket.io-protocol), regardless of any tooling used for automation / code generation.

#### Message Ack Object

| Field Name | Type                                                                             | Description                                                                                                                                                              |
| ---------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| args       | [Schema Object](https://www.asyncapi.com/docs/specifications/2.0.0#schemaObject) | Schema of the arguments that are passed as input to the acknowledgement callback function. In the case of multiple arguments, use the `array` type to express the tuple. |

In the future, the Message Ack Object may be extended with extra fields to enable additional documentation of the callback.
