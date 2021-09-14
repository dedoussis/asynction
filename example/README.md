# Socket.IO chat application using Asynction

This example is a fork of the chat application that is featured as a demo in the official Socket.IO website: <https://socket.io/demos/chat>.

The [original source](https://github.com/socketio/socket.io/tree/master/examples/chat) has been modified so that the Socket.IO server is implemented using Asynction.

## Layout

- `asyncapi.yml`: The specification that drives the Socket.IO server.
- `app.py`: The server implementation. Includes the event handlers as well as the construction of the `flask.Flask` and `flask_socketio.SocketIO` instances.
- `mock_app.py`: The mock server implementation.
- `client/`: The client implementation, using [express](https://expressjs.com/) and vanilla JavaScript.
- `Makefile`: Includes commands for launching the client and server instances.

## How to run it

Both of the server and client applications are dockerised and bundled together in a [docker-compose](https://docs.docker.com/compose/) setup.

### Using docker

```bash
$ make docker-run  # Launches both client and server
```

### Without docker

First make sure that you have python 3.7+ and node 12+ installed in your local environment.

```bash
$ make run-server  # Installs python deps and launches the server
$ make run-client  # Installs node.js deps and launches the client
```

## Use

Client: <http://localhost:3000>.  
Server: <http://localhost:5000>.

To connect to the bonus `/admin` Socket.IO namespace, use the `token` URL query param when accessing the client app: <http://localhost:3000?token=admin>.

## Mock server

```bash
$ make run-server-mock  # Listens to localhost:5000 by default
$ make run-client  # The same app client should seamingly integrate with the mock server
```
