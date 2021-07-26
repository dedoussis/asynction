NOOP=
SPACE=$(NOOP) $(NOOP)
PKG_VERSION=$(shell git describe --abbrev=0 --tags)

all-install: $(wildcard requirements*.txt)
	pip install -r $(subst $(SPACE), -r ,$?)

%-install: %.txt
	pip install -r $<

clean: clean-pyc clean-build clean-tests clean-mypy clean-docker

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

clean-docker:
	docker compose down

typecheck:
	mypy --package asynction --config-file setup.cfg

test-unit:
	pytest -vvv --mypy --cov=asynction --cov-report=xml tests/unit

test-integration:
	pytest -vvv --mypy tests/integration

test-e2e: clean
	docker compose up --build --detach asynction_server
	docker compose run test_runner

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
	PKG_VERSION=$(PKG_VERSION) python setup.py sdist bdist_wheel
	ls -l dist

docs/% example/%:
	$(MAKE) -C $(@D) $(@F:.%=%)

.PHONY: all-install clean clean-pyc clean-build clean-tests clean-mypy clean-docker typecheck test-unit test-integration test-e2e format lint release dist
