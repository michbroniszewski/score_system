# Common commands. Run `make help` for the list.
# Lint and tests run on the host (uv + npm), the same steps as CI.
# migrate and seed run inside the api container.

# Host ports from .env (if present); pytest uses DB_PORT to reach the test database.
-include .env
export DB_PORT

.PHONY: help install up down logs migrate seed openapi lint format test

help:
	@echo "install  install backend (uv) and frontend (npm) dependencies"
	@echo "up       build and start the Docker Compose environment"
	@echo "down     stop the environment (the database volume is kept)"
	@echo "logs     follow the logs of all services"
	@echo "migrate  apply database migrations (after make up)"
	@echo "seed     load the sample volleyball league (after make migrate)"
	@echo "openapi  regenerate the API schema snapshot backend/openapi.json"
	@echo "lint     ruff, mypy, eslint and vue-tsc"
	@echo "format   auto-format the backend code with ruff"
	@echo "test     backend (pytest, starts the db container) and frontend (vitest) tests"

install:
	cd backend && uv sync
	cd frontend && npm ci

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api score seed

openapi:
	cd backend && uv run score openapi > openapi.json

lint:
	cd backend && uv run ruff check
	cd backend && uv run ruff format --check
	cd backend && uv run mypy
	cd frontend && npm run lint
	cd frontend && npm run typecheck

format:
	cd backend && uv run ruff check --fix
	cd backend && uv run ruff format

# Integration tests need PostgreSQL: start only the db container and wait until healthy.
test:
	docker compose up -d --wait db
	cd backend && uv run pytest --cov=score_system
	cd frontend && npm test
