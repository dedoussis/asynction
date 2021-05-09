.. Asynction documentation master file, created by
   sphinx-quickstart on Tue May  4 07:16:13 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Asynction's documentation!
=====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Asynction SocketIO Server
-------------------------

The ``AsynctionSocketIO`` server is essentially a ``flask_socketio.SocketIO`` server with an additional factory classmethod.

.. autoclass:: asynction.AsynctionSocketIO
   :members: from_spec

Exceptions
----------

Asynction's exceptions to be caught via Flask-SocketIO error handlers.

.. autoclass:: asynction.AsynctionException
.. autoclass:: asynction.ValidationException
.. autoclass:: asynction.PayloadValidationException
.. autoclass:: asynction.BindingsValidationException
.. autoclass:: asynction.MessageAckValidationException

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
