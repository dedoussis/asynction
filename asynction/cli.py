import eventlet

eventlet.monkey_patch()  # noreorder

import argparse
from functools import singledispatch
from pathlib import Path
from typing import Optional

from flask import Flask
from importlib_metadata import PackageNotFoundError
from importlib_metadata import version

import asynction


def get_version() -> str:
    try:
        return version(asynction.__name__)
    except PackageNotFoundError:
        return "not-found"


class AsynctionNamespace(argparse.Namespace):
    command: str
    spec: Path
    server: Optional[str]
    without_validation: bool


class RunNamespace(AsynctionNamespace):
    host: str
    port: int
    debugger: bool


class MockNamespace(AsynctionNamespace):
    mock_command: str
    custom_formats_sample_size: int


class RunMockNamespace(MockNamespace, RunNamespace):
    subscription_task_interval: float
    max_workers: int


def build_parser() -> argparse.ArgumentParser:
    formatter_class = argparse.ArgumentDefaultsHelpFormatter

    parser = argparse.ArgumentParser(
        asynction.__name__, formatter_class=formatter_class
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )
    parser.add_argument(
        "--spec",
        "-s",
        type=Path,
        default=Path.cwd().joinpath("asyncapi.yaml"),
        help="Path to the AsyncAPI specification YAML file",
    )
    parser.add_argument(
        "--without-validation",
        default=False,
        action="store_true",
        help="Disable Asynction's default validation",
    )
    parser.add_argument(
        "--server",
        required=False,
        help="The server to pick from the AsyncAPI servers object",
    )

    subparsers = parser.add_subparsers(title="Sub-commands", dest="command")
    mock_parser = subparsers.add_parser(
        "mock",
        formatter_class=formatter_class,
        help="Utilities for the mock Asynction SocketIO server",
    )
    mock_parser.add_argument(
        "--custom-formats-sample-size",
        type=int,
        default=20,
        help="The ammout of the Faker provider samples to be used "
        "for each custom string format. "
        "Hypotheses uses these samples to generate fake data. "
        "Set to 0 if custom formats are not needed.",
    )

    mock_subparsers = mock_parser.add_subparsers(
        title="Mock sub-commands", dest="mock_command"
    )
    run_mock_parser = mock_subparsers.add_parser(
        "run",
        formatter_class=formatter_class,
        help="Run a mock Asynction SocketIO server",
    )
    run_mock_parser.add_argument(
        "--host", default="0.0.0.0", help="The interface to bind to"
    )
    run_mock_parser.add_argument(
        "--port", "-p", type=int, default=5000, help="The port to bind to"
    )
    run_mock_parser.add_argument(
        "--subscription-task-interval",
        type=float,
        default=1.0,
        help="How often (in seconds) a subscription task "
        "(thread that emits an event to a connected client) is scheduled.",
    )
    run_mock_parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="The maximum number of workers to be started for the purposes "
        "of executing background subscription tasks.",
    )

    run_mock_parser.add_argument(
        "--debugger",
        "-d",
        action="store_true",
        help="Enable the debugger",
    )

    return parser


@singledispatch
def command(args: AsynctionNamespace, parser: argparse.ArgumentParser) -> None:
    if args.command == "mock":
        return command(MockNamespace(**vars(args)), parser)

    parser.print_help()


@command.register
def _mock_command(args: MockNamespace, parser: argparse.ArgumentParser) -> None:
    if args.mock_command == "run":
        return command(RunMockNamespace(**vars(args)), parser)

    parser.parse_args([args.command, "--help"])


@command.register
def _run_mock_command(args: RunMockNamespace, parser: argparse.ArgumentParser) -> None:
    flask_app = Flask(__name__)

    mock_asio = asynction.MockAsynctionSocketIO.from_spec(
        spec_path=args.spec,
        validation=not args.without_validation,
        server_name=args.server,
        logger=args.debugger,
        app=flask_app,
        cors_allowed_origins="*",
        custom_formats_sample_size=args.custom_formats_sample_size,
    )

    mock_asio.run(
        app=flask_app,
        debug=args.debugger,
        log_output=args.debugger,
        host=args.host,
        port=args.port,
        subscription_task_interval=args.subscription_task_interval,
        max_worker_number=args.max_workers,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args(namespace=AsynctionNamespace())
    return command(args, parser)
