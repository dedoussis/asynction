# Contributing

Asynction is still at an early beta stage and any contribution towards improving the framework would be greatly appreciated.

The current areas of focus are:

* Productionizing the library
* Documentation

## Table of Contents 📖

1. [Roadmap](#roadmap)
1. [Support questions & reporting bugs](#support-questions--reporting-bugs)
1. [Development](#development)
    1. [Project structure](#project-structure)
    1. [Environment setup](#environment-setup)
    1. [Coding style](#coding-style)
    1. [Checks & Testing](#checks--testing)
    1. [Docs](#docs)
1. [Release](#release)
1. [Finally](#finally)

## Roadmap

* Documenting examples and tutorials of using Asynction.
* Improving the existing generated documentation.
* Mock server support.
* Exposing an [AsyncAPI playground](https://playground.asyncapi.io/) via a Flask route, in a similar manner to how Connexion exposes a Swagger UI.
* E2E testing suite (using a dockerised setup)
* Type casting: Whenever possible Asynction should try to parse the argument values and do type casting to the related Python native values.
* Dynamic rendering of the [AsyncAPI](https://www.asyncapi.com/) spec. Could use [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/) to allow the parametrisation of the spec.
* Authentication à la [Connexion](https://connexion.readthedocs.io/en/latest/security.html).

The OpenAPI counterparts of Asynction are [Connexion](https://github.com/zalando/connexion) for python and [openapi-backend](https://github.com/anttiviljami/openapi-backend) for Node.js. These tools provide a great source of inspiration for the above roadmap.

If you have any roadmap ideas or feature requests please submit them via the [issue tracker](https://github.com/dedoussis/asynction/issues).

## Support questions & reporting bugs

You are welcome to use the [issue tracker](https://github.com/dedoussis/asynction/issues) of this repository for questions about using Asynction. Make sure that the `question` label is applied.

Reporting a bug should also go through the [issue tracker](https://github.com/dedoussis/asynction/issues).

## Development

### Project structure

```
root/
├───asynction/
├───docs/
├───tests/
│   ├───integration/
│   └───unit/
├───Makefile
├───requirements-dev.txt
├───requirements-test.txt
├───requirements.txt
└───...
```

* The `asynction` directory is a python package that contains the runtime source of the framework.
* `docs` is the source directory of the [Sphinx](https://www.sphinx-doc.org/) documentation hosted at <https://asynction.dedouss.is>.
* `tests` is the source of the entire test suite, consisting of unit and integration tests.
* The top level `Makefile` is a toolbox of useful commands for installing dependencies as well as testing, linting and packaging the code. It is also used as the entrypoint interface for all CI/CD operations.

### Environment setup

Use python3.7 or higher.

1. [Create and activate a virtual environment](https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments)

1. Upgrade pip and setuptools

    ```bash
    $ python -m pip install --upgrade pip setuptools
    ```

1. Install all the requirements

    ```bash
    $ make all-install
    ```

    or install a subset of the requirements depending on the task

    ```bash
    $ make requirements-dev-install  # Dependecies useful for local development
    $ make requirements-test-install  # Testing dependencies
    $ make requirements-install  # Runtime dependencies
    ```

1. Install the pre-commit hooks

    ```bash
    $ pre-commit install
    ```

### Coding style

* All Python code must follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines.
* Type annotations are mandatory (even in tests). Avoid the use of `typing.Any` and `# type: ignore`.
* All parts of the public API (exposed via `asynction.__init__.py`) should be documented with docstrings.

__Make sure you run `pre-commit` before every commit!__

### Checks & Testing

```bash
$ make lint  # Checks for flake8 linting, black formatting, and sequence of imports (isort)
$ make typecheck  # mypy checks

$ make test-unit  # unit testing suite
$ make test-integration  # integration testing suite
```

### Docs

There is a [Sphinx](https://www.sphinx-doc.org/) setup located at `/docs`.

From the root directory:

```bash
$ make requirements-dev-install  # To build the docs, you first need to have the dev dependencies installed.
$ make docs/html
```

Open `docs/_build/html/index.html` in your browser to view the generated documentation.

## Release

Asynction releases are driven by git tags and [GitHub releases](https://docs.github.com/en/github/administering-a-repository/releasing-projects-on-github/managing-releases-in-a-repository).

The cut of a git tag will trigger a release workflow. Note that tagging should follow the [SemVer](https://semver.org/) specification.

The release workflow:

1. Builds the source and wheel distributions
1. Builds the Sphinx documentation
1. Publishes the distributions to <https://test.pypi.org/project/asynction/>
1. Publishes the distributions to <https://pypi.org/project/asynction/>
1. Publishes the HTML docs to <https://asynction.dedouss.is>

A changedlog can be found in the [releases](https://github.com/dedoussis/asynction/releases) section of the repository.

The changelog is autogenerated using the [release-drafter GitHub Action](https://github.com/marketplace/actions/release-drafter).

## Finally

Thank you for considering contributing to Asynction ❤️
