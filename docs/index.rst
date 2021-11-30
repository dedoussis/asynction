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

.. automodule:: asynction.server

.. autoclass:: asynction.AsynctionSocketIO
   :members: from_spec

Mock Asynction Server
-------------------------

.. automodule:: asynction.mock_server

.. autoclass:: asynction.MockAsynctionSocketIO
   :members: from_spec

   .. automethod:: run


Exceptions
----------

.. automodule:: asynction.exceptions

.. autoexception:: asynction.AsynctionException
.. autoexception:: asynction.ValidationException
.. autoexception:: asynction.PayloadValidationException
.. autoexception:: asynction.BindingsValidationException
.. autoexception:: asynction.MessageAckValidationException
.. autoexception:: asynction.SecurityException

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
