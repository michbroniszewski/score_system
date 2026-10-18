# Common commands. Run `make help` for the list.
# Lint and tests run on the host (uv + npm), the same steps as CI.

.PHONY: help install up down logs lint format test

help:
	@echo "install  install backend (uv) and frontend (npm) dependencies"
	@echo "up       build and start the Docker Compose environment"
	@echo "down     stop the environment (the database volume is kept)"
	@echo "logs     follow the logs of all services"
	@echo "lint     ruff, mypy, eslint and vue-tsc"
	@echo "format   auto-format the backend code with ruff"
	@echo "test     backend (pytest) and frontend (vitest) tests"

install:
	cd backend && uv sync
	cd frontend && npm ci

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

lint:
	cd backend && uv run ruff check
	cd backend && uv run ruff format --check
	cd backend && uv run mypy
	cd frontend && npm run lint
	cd frontend && npm run typecheck

format:
	cd backend && uv run ruff check --fix
	cd backend && uv run ruff format

test:
	cd backend && uv run pytest --cov=score_system
	cd frontend && npm test
