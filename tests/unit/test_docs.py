from flask import Flask

from asynction.docs import current_spec
from asynction.docs import set_current_spec
from asynction.types import AsyncApiSpec
from asynction.types import Info


def test_current_spec(server_info: Info) -> None:
    app = Flask(__name__)
    spec = AsyncApiSpec(asyncapi="2.3.0", channels={}, info=server_info)
    app.config["ASYNCAPI_SPEC_OBJ"] = spec
    assert current_spec(app) == spec


def test_set_current_spec(server_info: Info) -> None:
    app = Flask(__name__)
    spec = AsyncApiSpec(asyncapi="2.3.0", channels={}, info=server_info)
    set_current_spec(app, spec)
    assert app.config["ASYNCAPI_SPEC_OBJ"] == spec
