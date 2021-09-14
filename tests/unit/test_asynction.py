"""Tests that assert backwards compatibility of the package's API"""

import asynction


def test_assynction_all_attrs():
    for attr in [
        "AsynctionSocketIO",
        "AsynctionException",
        "ValidationException",
        "PayloadValidationException",
        "BindingsValidationException",
        "MessageAckValidationException",
        "MockAsynctionSocketIO",
    ]:
        assert hasattr(asynction, attr)
        assert attr in asynction.__all__
