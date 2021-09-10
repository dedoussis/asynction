#!/usr/bin/env python3
import os
from pathlib import Path

from flask import Flask

from asynction import MockAsynctionSocketIO

flask_app = Flask(__name__)

mock_asio = MockAsynctionSocketIO.from_spec(
    spec_path=Path(__file__).parent.joinpath("asyncapi.yml"),
    validation=False,
    server_name=os.environ.get("ASYNCAPI_SERVER_NAME", "demo"),
    logger=True,
    async_mode="gevent",
    app=flask_app,
    cors_allowed_origins="*",
    subscription_task_interval=float(os.environ.get("SUBSCRIPTION_TASK_INTERVAL", "1")),
)

if __name__ == "__main__":
    mock_asio.run(app=flask_app, debug=True, log_output=True, host="0.0.0.0")
