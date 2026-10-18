# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working rules (set by the owner, mandatory)

- **Never commit or push without Michal's explicit consent.** Prepare changes locally, show them (diff, test results) and wait for approval. Consent for one commit does not cover the next one.
- **Ask, don't assume.** When a task can be read more than one way, present the options with a recommendation and ask.
- **Tests from the start, CI kept up to date.** Every logic change comes with tests; when commands, dependencies or structure change, update `.github/workflows/` too.
- **English is the project language.** Everything in the repository is written in English: code, identifiers, comments, docstrings, docs, commit messages and PR descriptions.

## Coding guidelines (karpathy-guidelines)

1. **Think before coding.** State assumptions explicitly. If something is unclear, stop and ask. If a simpler approach exists, say so.
2. **Simplicity first.** Minimum code that solves the problem. No features, abstractions or configurability nobody asked for. The system's universality comes from rule presets (see below), not from speculative layers.
3. **Surgical changes.** Touch only what the task requires. Don't "improve" adjacent code or formatting. Remove only what your change made unused; mention unrelated dead code instead of deleting it.
4. **Goal-driven execution.** Turn tasks into verifiable criteria (e.g. "write a test that reproduces the bug, then fix it"). For multi-step tasks, state a short plan: step → how it is verified.

## Project overview

A universal system for running competitions (amateur league, tournament, any format), configurable per discipline, regulations and scoring rules. Scope: teams with rosters, statistics and details; standings computed automatically; an editable fixture schedule. Browser first, a mobile app later.

The full architecture and stage plan lives in `docs/architecture.md`.

## Architecture decisions

- **Backend:** Python 3.12+, FastAPI + Pydantic v2, SQLAlchemy 2.0 + Alembic, PostgreSQL.
- **Frontend:** Vue 3 + TypeScript + Vite, as a PWA.
- **Tooling:** uv (dependencies), Docker Compose (local environment; the owner wants to learn Docker through this project, so explain and comment Docker configuration), Makefile.
- **Hosting:** no paid server. The system runs locally (Docker) and data is edited locally; `make export` writes a JSON snapshot to `data/export/`, and GitHub Actions publishes a read-only site from it to GitHub Pages. The database never leaves the owner's machine.
- **First discipline:** volleyball, round robin. Points: 3:0 and 3:1 = 3, 3:2 = 2, 2:3 = 1, 1:3 and 0:3 = 0. Standings order: points, set ratio, small-points ratio (may be extended later).

## Architecture (target)

Layers, each independent of the one above it:

- `domain/`: pure Python, no I/O (models, rules engine, `compute_standings`, fixture generator). Standings are always derived from matches, never stored.
- `application/`: use cases / services.
- `infrastructure/`: SQLAlchemy, repositories, static export.
- `api/`: FastAPI routers under `/api/v1`.

Principles that are easy to trip over:

- **API-first for mobile.** API v1 is the only client contract; the static JSON export uses exactly the same format as the API responses, so the Pages frontend and the future mobile app read data identically. An OpenAPI schema snapshot is kept in the repo; changing it is a deliberate decision.
- **Universality through configuration.** Discipline rules are YAML presets in `backend/presets/` (validated with Pydantic). Tiebreakers are a list of pluggable strategies. A new discipline means a new preset and, if needed, one new strategy, with no changes elsewhere.
- Dates in UTC (ISO 8601), stable identifiers (UUID/slug), authentication planned as tokens (not cookie sessions).

## Commands

Lint and tests run on the host (uv for the backend, npm for the frontend), with the same steps as CI. `make help` lists all targets.

- `make install`: install backend (`uv sync`) and frontend (`npm ci`) dependencies.
- `make up` / `make down` / `make logs`: start, stop and follow the Docker Compose environment (`db`, `api`, `frontend`, plus `adminer` from `compose.override.yaml`).
- `make migrate` / `make seed`: apply Alembic migrations / load the sample league (`score seed`), both inside the `api` container.
- `make lint`: `ruff check`, `ruff format --check`, `mypy` (strict), `eslint`, `vue-tsc`.
- `make format`: auto-fix and format the backend with ruff.
- `make test`: starts the `db` container, then backend `pytest --cov` and frontend `vitest`.
- Single backend test: `cd backend && uv run pytest tests/test_file.py::test_name`.
- Single frontend test: `cd frontend && npx vitest run src/path/file.spec.ts`.
- New migration: `cd backend && uv run alembic revision --autogenerate -m "..."` (db running), then review it.
- Planned in later stages: `make export`.

The Python project lives in `backend/` (its own `pyproject.toml` and `uv.lock`), the frontend in `frontend/`. CI (`.github/workflows/ci.yml`) runs the backend checks, the frontend checks and build, and `docker compose build`.

Domain tests run without a database (`uv run pytest tests/domain`). Tests in `tests/infrastructure/` need PostgreSQL (the Compose `db` service locally, a service container in CI): they recreate the `score_system_test` database (`TEST_DATABASE_URL`), build the schema by running the migrations, and roll back each test.
