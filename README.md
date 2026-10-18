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
```

Then open:

- API health check: http://localhost:8000/api/v1/health
- API docs (Swagger UI): http://localhost:8000/docs
- Frontend: http://localhost:5173
- Adminer (database browser): http://localhost:8080 (system PostgreSQL, server `db`)

`make down` stops everything; database data stays in the `db-data` volume.

## Development

```sh
make lint    # ruff, mypy, eslint, vue-tsc
make test    # pytest and vitest
make help    # all targets
```

Optional git hooks: `cd backend && uv run pre-commit install`.
