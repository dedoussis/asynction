#!/usr/bin/env python3
import os
from logging import getLogger
from pathlib import Path
from random import sample

from faker import Faker
from flask import Flask
from hypothesis.strategies import sampled_from

from asynction import MockAsynctionSocketIO

logger = getLogger(__name__)
flask_app = Flask(__name__)
faker = Faker()

CUSTOM_FORMATS = {
    "first_name": sampled_from([faker.first_name() for _ in range(30)]),
    "message": sampled_from([faker.sentence() for _ in range(200)]),
}

mock_asio = MockAsynctionSocketIO.from_spec(
    spec_path=Path(__file__).parent.joinpath("asyncapi.yml"),
    server_name=os.environ.get("ASYNCAPI_SERVER_NAME", "demo"),
    logger=logger,
    async_mode="gevent",
    app=flask_app,
    cors_allowed_origins="*",
    custom_format_samples=CUSTOM_FORMATS,
)

if __name__ == "__main__":
    mock_asio.run(app=flask_app, log_output=logger, host="0.0.0.0")
