NOOP=
SPACE=$(NOOP) $(NOOP)
DOCKER_REPO=dedoussis/asynction
PKG_VERSION=$(shell git describe --abbrev=0 --tags)
DOCKER_TAG=$(DOCKER_REPO):$(PKG_VERSION)

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
	rm -rf .hypothesis

clean-mypy:
	rm -rf .mypy_cache

typecheck:
	mypy --package asynction --config-file setup.cfg

test-unit:
	pytest -vvv --mypy --cov asynction --cov-report xml --cov-report term tests/unit

test-integration:
	pytest -vvv --mypy tests/integration

test-e2e: clean
	docker-compose -f tests/e2e/docker-compose.yml up --build --abort-on-container-exit --exit-code-from test_runner

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

docker-build:
	docker build . -t $(DOCKER_TAG) --build-arg VERSION=$(PKG_VERSION)

docker-push:
	docker push $(DOCKER_TAG)
	docker tag $(DOCKER_TAG) $(DOCKER_REPO):latest
	docker push $(DOCKER_REPO):latest

.PHONY: all-install clean clean-pyc clean-build clean-tests clean-mypy typecheck test-unit test-integration test-e2e format lint release dist docker-build docker-push
