import argparse
from pathlib import Path
from unittest.mock import ANY
from unittest.mock import patch

from faker import Faker
from importlib_metadata import PackageNotFoundError

import asynction
from asynction.cli import AsynctionNamespace
from asynction.cli import MockNamespace
from asynction.cli import RunMockNamespace
from asynction.cli import build_parser
from asynction.cli import command
from asynction.cli import get_version


def test_get_version_found(faker: Faker):
    mock_version = faker.pystr()
    with patch.object(asynction.cli, "version", return_value=mock_version):
        assert get_version() == mock_version


def test_get_version_not_found():
    with patch.object(asynction.cli, "version", side_effect=PackageNotFoundError()):
        assert get_version() == "not-found"


def test_build_parser():
    parser = build_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_parser_mock_run_parsing_defaults():
    parser = build_parser()
    args = parser.parse_args(["mock", "run"])
    assert args.spec == Path.cwd().joinpath("asyncapi.yaml")
    assert not args.server
    assert not args.without_validation
    assert not args.debugger
    assert args.host == "0.0.0.0"
    assert args.port == 5000
    assert not args.debugger
    assert args.command == "mock"
    assert args.mock_command == "run"
    assert args.subscription_task_interval == 1.0
    assert args.max_workers == 8
    assert args.custom_formats_sample_size == 20


def test_parser_mock_run_parsing_non_defaults(faker: Faker):
    parser = build_parser()

    spec_file_dir = faker.word()
    server_name = faker.word()
    custom_formats_sample_size = faker.pyint()
    max_workers = faker.pyint()
    subscription_task_interval = faker.pyfloat()
    host = faker.pystr()
    port = faker.pyint()

    args = parser.parse_args(
        [
            "--spec",
            f"./{spec_file_dir}/asyncapi.yaml",
            "--without-validation",
            "--server",
            server_name,
            "mock",
            "--custom-formats-sample-size",
            str(custom_formats_sample_size),
            "run",
            "--max-workers",
            str(max_workers),
            "--subscription-task-interval",
            str(subscription_task_interval),
            "--host",
            host,
            "--port",
            str(port),
            "--debugger",
        ]
    )
    assert args.spec == Path(spec_file_dir).joinpath("asyncapi.yaml")
    assert args.server == server_name
    assert args.without_validation
    assert args.debugger
    assert args.host == host
    assert args.port == port
    assert args.debugger
    assert args.command == "mock"
    assert args.mock_command == "run"
    assert args.subscription_task_interval == subscription_task_interval
    assert args.max_workers == max_workers
    assert args.custom_formats_sample_size == custom_formats_sample_size


def test_command_with_asynction_namespace_and_no_command_prints_help():
    parser = build_parser()
    with patch.object(parser, "print_help") as print_help_mock:
        command(AsynctionNamespace(command=None), parser)
        print_help_mock.assert_called_once()


def test_command_with_mock_namespace_and_no_command_prints_help():
    parser = build_parser()
    with patch.object(parser, "parse_args") as parse_args_mock:
        command(MockNamespace(command="mock", mock_command=None), parser)
        parse_args_mock.assert_called_once_with(["mock", "--help"])


def test_command_with_mock_run_namespace(faker: Faker):
    parser = build_parser()

    root_command = ("mock",)
    mock_command = "run"
    spec = Path(__file__).joinpath(faker.word())
    server_name = faker.word()
    without_validation = False
    subscription_task_interval = faker.pyfloat()
    max_workers = faker.pyint()
    custom_formats_sample_size = faker.pyint()
    debugger = True
    host = faker.pystr()
    port = faker.pyint()

    with patch.object(asynction, "MockAsynctionSocketIO") as mock_asio_mock:
        command(
            RunMockNamespace(
                command=root_command,
                mock_command=mock_command,
                spec=spec,
                server=server_name,
                without_validation=without_validation,
                subscription_task_interval=subscription_task_interval,
                max_workers=max_workers,
                custom_formats_sample_size=custom_formats_sample_size,
                debugger=debugger,
                host=host,
                port=port,
            ),
            parser,
        )

        mock_asio_mock.from_spec.assert_called_once_with(
            spec_path=spec,
            validation=not without_validation,
            server_name=server_name,
            custom_formats_sample_size=custom_formats_sample_size,
            async_mode="threading",
            logger=debugger,
            app=ANY,
            cors_allowed_origins="*",
        )

        mock_asio_mock.from_spec.return_value.run.assert_called_once_with(
            app=ANY,
            host=host,
            port=port,
            max_worker_number=max_workers,
            subscription_task_interval=subscription_task_interval,
            debug=debugger,
            log_output=debugger,
        )
