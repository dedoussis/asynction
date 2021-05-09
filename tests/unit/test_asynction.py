"""Tests that assert backwards compatibility of the package's API"""

import asynction


def test_asynction_socket_io_attr():
    assert hasattr(asynction, "AsynctionSocketIO")


def test_asynction_exceptiions_attr():
    assert hasattr(asynction, "AsynctionException")
    assert hasattr(asynction, "ValidationException")
    assert hasattr(asynction, "PayloadValidationException")
    assert hasattr(asynction, "BindingsValidationException")
    assert hasattr(asynction, "MessageAckValidationException")
