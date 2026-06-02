.PHONY: help install dev test test-cov lint format typecheck migrate makemigrations shell superuser clean

help:  ## Pokaż dostępne komendy
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Zainstaluj zależności (wymaga uv)
	uv sync
	uv run pre-commit install

dev:  ## Uruchom serwer deweloperski
	uv run python manage.py runserver

test:  ## Uruchom testy
	uv run pytest

test-cov:  ## Uruchom testy z pokryciem
	uv run pytest --cov --cov-report=term-missing --cov-report=html

lint:  ## Uruchom linter (ruff)
	uv run ruff check .
	uv run ruff format --check .

format:  ## Sformatuj kod (ruff)
	uv run ruff format .
	uv run ruff check --fix .

typecheck:  ## Sprawdź typy (mypy)
	uv run mypy .

migrate:  ## Uruchom migracje
	uv run python manage.py migrate

makemigrations:  ## Wygeneruj migracje
	uv run python manage.py makemigrations

shell:  ## Uruchom shell Django
	uv run python manage.py shell

superuser:  ## Utwórz superusera
	uv run python manage.py createsuperuser

clean:  ## Usuń artefakty buildów i cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf htmlcov .coverage coverage.xml
