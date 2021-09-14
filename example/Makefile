docker-run: docker-build
	docker compose up

docker-build: 
	docker compose build

docker-clean:
	docker compose down

run-server: install-server-requirements
	python app.py

run-server-mock: install-server-mock-requirements
	python mock_app.py

run-client: install-client-requirements
	npm run --prefix client start

install-server-requirements:
	pip install -r requirements.txt

install-server-mock-requirements: install-server-requirements
	pip install -r requirements-mock.txt

install-client-requirements:
	npm install --prefix client

typecheck-server:
	mypy --module app --ignore-missing-imports

lint-client:
	npm run --prefix client pretty:check

.PHONY: docker-run docker-build docker-clean run-server run-server-mock run-client install-server-requirements install-server-mock-requirements install-client-requirements lint-client
