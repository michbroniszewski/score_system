# score_system

A universal system for running amateur leagues and tournaments, configurable per discipline and regulations. See [docs/architecture.md](docs/architecture.md) for the architecture and stage plan.

## Requirements (Linux)

- [uv](https://docs.astral.sh/uv/) (Python 3.12+ is installed by uv if missing)
- Node.js 22 and npm
- Docker with the Compose plugin

## Quick start

```sh
cp .env.example .env    # local settings (database credentials, ports)
make install            # backend and frontend dependencies
make up                 # start db, api, frontend and adminer in Docker
make migrate            # create the database tables
make seed               # optional: load a sample volleyball league
```

Then open:

- API health check: http://localhost:8000/api/v1/health
- API docs (Swagger UI): http://localhost:8000/docs
- Frontend: http://localhost:5173 (the public site, reading the local API)
- Adminer (database browser): http://localhost:8080 (system PostgreSQL, server `db`)

In Swagger UI you can try the whole API: create a competition, enter teams, generate fixtures, record results and read the standings. After `make seed`, see for example `GET /api/v1/competitions/sample-volleyball-league/standings`.

`make down` stops everything; database data stays in the `db-data` volume.

## Publishing to GitHub Pages

The database stays on your machine; only a read-only JSON snapshot is published.

1. With `make up` running, `make export` writes the snapshot to `data/export/api/v1/`. Each file is the API response at the same path, e.g. `competitions/<slug>/standings.json` is `GET /api/v1/competitions/<slug>/standings`.
2. Commit and push `data/export/` to `main`. The `Pages` workflow builds the frontend and publishes it with the snapshot at `https://<owner>.github.io/<repo>/` (data under `api/v1/`).

Once per repository: in Settings → Pages, set the source to "GitHub Actions".

## Development

```sh
make lint    # ruff, mypy, eslint, vue-tsc
make test    # pytest (starts the db container) and vitest
make help    # all targets
```

Integration tests use a separate `score_system_test` database, recreated on every run. If you change the database credentials in `.env`, set `TEST_DATABASE_URL` to match.

New database migration after changing `backend/src/score_system/infrastructure/orm.py` (with `make up` running): `cd backend && uv run alembic revision --autogenerate -m "describe the change"`, review the generated file in `backend/migrations/versions/`, then `make migrate`.

Optional git hooks: `cd backend && uv run pre-commit install`.
