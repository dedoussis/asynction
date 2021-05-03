NOOP=
SPACE=$(NOOP) $(NOOP)
PGK_VERSION=$(shell git describe --abbrev=0 --tags)

all-install: $(wildcard requirements*.txt)
	pip install -r $(subst $(SPACE), -r ,$?)

%-install: %.txt
	pip install -r $<

clean: clean-pyc clean-build clean-tests clean-mypy

clean-pyc:
	find . -name '*.pyc' -exec rm -rf {} +
	find . -name '*.pyo' -exec rm -rf {} +
	find . -name '*~' -exec rm -rf  {} +

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

clean-tests:
	rm -rf .pytest_cache
	rm -rf .coverage* coverage.*

clean-mypy:
	rm -rf .mypy_cache

typecheck:
	mypy --package asynction --config-file setup.cfg

test-unit:
	pytest -vvv --mypy --cov=asynction --cov-report=xml tests/unit

test-integration:
	pytest -vvv --mypy tests/integration

format:
	black .
	isort .

lint:
	flake8 asynction tests
	black --check --diff .
	isort . --check-only

release: dist
	twine upload dist/*

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

.PHONY: all-install clean clean-pyc clean-build clean-tests clean-mypy typecheck test-unit test-integration format lint release dist
