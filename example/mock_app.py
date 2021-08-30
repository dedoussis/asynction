#!/usr/bin/env python3
import os
from logging import getLogger
from pathlib import Path

from faker import Faker
from flask import Flask

from asynction import MockAsynctionSocketIO

logger = getLogger(__name__)
flask_app = Flask(__name__)
faker = Faker()

mock_asio = MockAsynctionSocketIO.from_spec(
    spec_path=Path(__file__).parent.joinpath("asyncapi.yml"),
    server_name=os.environ.get("ASYNCAPI_SERVER_NAME", "demo"),
    logger=logger,
    async_mode="gevent",
    app=flask_app,
    cors_allowed_origins="*",
)

if __name__ == "__main__":
    mock_asio.run(app=flask_app, log_output=logger, host="0.0.0.0")
