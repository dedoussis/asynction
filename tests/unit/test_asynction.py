"""Tests that assert backwards compatibility of the package's API"""

import asynction


def test_asynction_socket_io_attr():
    assert hasattr(asynction, "AsynctionSocketIO")
