# Score System: architecture and implementation plan

> Status: all architecture decisions made (section 12). Last updated 2026-10-18.

## 1. Goal and scope

A universal system for running competitions (amateur league, tournament, any format), configurable per discipline, regulations and scoring rules.

**MVP scope (version 1):**
- teams: details, roster (players with membership history), team and player statistics,
- standings computed automatically from the regulations (points, tiebreakers),
- fixtures: generation (e.g. round robin) and manual editing (date, time, venue, postponement, walkover),
- entering match results and events (points, aces, blocks... depending on the discipline),
- browser access, with an architecture ready for a future mobile app.

**Out of MVP (later):** user accounts and roles, notifications, the mobile app, live coverage, multiple leagues with separate administrators, CSV import/export.

## 2. Core principle: API and domain core first

So that the mobile app does not force a redesign, the system is split into layers, each independent of the one above it:

```
┌───────────────────────────────────────────────────────────────┐
│ Clients: browser (now) · mobile app (later)                    │
└───────────────▲───────────────────────────────▲───────────────┘
                │ JSON (same contract)           │
┌───────────────┴───────────────┐  ┌────────────┴──────────────┐
│ HTTP API (FastAPI, OpenAPI)   │  │ Static JSON export         │
│ – local / future server       │  │ – GitHub Pages (read-only) │
└───────────────▲───────────────┘  └────────────▲──────────────┘
                │                               │
┌───────────────┴───────────────────────────────┴──────────────┐
│ Application layer (services, use cases)                       │
├───────────────────────────────────────────────────────────────┤
│ Domain core (pure Python, no I/O):                            │
│  rules · standings · fixture generator · statistics           │
├───────────────────────────────────────────────────────────────┤
│ Data repositories (SQLAlchemy) → PostgreSQL (Docker)          │
└───────────────────────────────────────────────────────────────┘
```

- **Domain core**: pure functions and models (Pydantic/dataclasses), unit-testable without a database or HTTP.
- **API**: the only contract for clients. The OpenAPI schema is generated automatically and can later be used to generate a mobile client (TypeScript/Dart/Kotlin).
- **Static export**: writes the same API responses as JSON files (e.g. `api/v1/competitions/1/standings.json`), so the GitHub Pages frontend and the future mobile app read data in an identical format whether or not a server is behind it.

## 3. Hosting without a server

GitHub Pages serves **static files only**; it cannot run Python or a database per request. Options considered (chosen: **A**):

| Option | How it works | Data editing | Pros | Cons |
|---|---|---|---|---|
| **A. Local admin + static publishing** (CHOSEN) | The administrator runs the system locally (Docker Compose: FastAPI + PostgreSQL) and edits data there. A data snapshot is exported to the repo; GitHub Actions builds the site and publishes it to Pages. | Locally, then commit/push. | Zero cost, full Python, same architecture as the target. | Only someone with the repo and a local environment can edit. |
| **B. Data as files in the repo** | Results and fixtures in YAML files, edited on GitHub (web editor or Issue form → Action updates the file). Actions recompute standings and publish. | Through GitHub (also from a phone). | No local environment needed for editing. | Clunky, "technical" editing. |
| **C. Free external backend** | Frontend on Pages, the same FastAPI image on a free host (e.g. Render, Koyeb), Postgres on a free plan (e.g. Neon, Supabase). | Normal online admin. | A real online app, multiple editors. | Goes beyond GitHub; free-tier limits change; the backend sleeps when idle. |

Decision: **A now, with code ready for C later** (the same FastAPI Docker image can run on a host without client changes).

**Publishing flow in option A:**
1. Locally: `make up` starts the containers; data is edited in the admin UI (or via the API).
2. `make export` writes a data snapshot to `data/export/` (JSON files in the API v1 format).
3. With the owner's consent: commit + push the snapshot to `main`.
4. GitHub Actions (`pages.yml`) builds the Vue frontend with that snapshot and publishes it to Pages.

The PostgreSQL database never leaves the owner's machine; only an explicit read-only snapshot goes into the repo.

## 4. Domain model (universal)

Universality comes from separating the **competition structure** from the **discipline rules**.

### 4.1 Entities

- **Discipline**: name, rules preset (volleyball, football, basketball, e-sports...), statistic definitions.
- **RuleSet**: points per result, whether draws are allowed, result structure (score / sets with points / games), ordered tiebreakers, walkover (default result), point penalties.
- **StatDefinition**: statistic type (point, ace, block, goal, card...), level (player/team), aggregation (sum, average, max).
- **Competition** → **Season** → **Stage** (league, groups, play-off) → **Group** (one standings table).
- **Team**: name, short name, crest, contact, description, home venue.
- **Player**: personal data (scope to be decided with GDPR in mind), position, number.
- **RosterEntry**: player ↔ team ↔ season, from–to, number, role (captain). Transfer history without overwriting data.
- **Venue**.
- **Match**: stage/group, round, home, away, date and time, venue, status (scheduled, played, postponed, cancelled, walkover).
- **MatchResult**: result shaped by the RuleSet (e.g. `{"home": 3, "away": 1}` or a list of sets).
- **MatchEvent**: match event (type from StatDefinition, player, team, minute/set, value).

### 4.2 Rules engine (core)

- `compute_standings(matches, ruleset) -> Standings`: a pure function; standings are always reproducible from matches (never stored, cache only).
- Tiebreakers as a **list of pluggable strategies** (e.g. `points`, `wins`, `set_ratio`, `small_points_ratio`, `head_to_head_points`, `goal_difference`, `draw_lots`). A new discipline means new configuration and, if needed, one new strategy, with no changes elsewhere.
- Fixture generator: round robin (circle method, single or double), groups, knockout bracket; Swiss system later.
- Discipline presets in YAML files (`presets/volleyball.yaml`, ...), validated with a Pydantic schema.

First preset (volleyball, round robin):

```yaml
discipline: volleyball
result_format: sets            # score | sets | custom
sets_to_win: 3                 # best of five
set_points: {regular: 25, tiebreak: 15, min_lead: 2}
allow_draw: false
points:                        # [winner, loser] points by set result
  "3:0": [3, 0]
  "3:1": [3, 0]
  "3:2": [2, 1]
walkover_set: [25, 0]          # every set of a walkover: 3:0, small points 75:0
tiebreakers: [points, set_ratio, small_points_ratio]
stats:
  - {code: points_scored, level: player, aggregate: sum}
  - {code: aces, level: player, aggregate: sum}
  - {code: blocks, level: player, aggregate: sum}
  - {code: mvp, level: player, aggregate: sum}
```

Further disciplines (e.g. football with `result_format: score` and draws) are added as new preset files.

## 5. Technology stack

| Area | Choice | Notes |
|---|---|---|
| Language | Python 3.12+ | |
| Project management | **uv** (dependencies, venv, lock) | also used inside the Docker image |
| Backend / API | **FastAPI** + Pydantic v2 | automatic OpenAPI for the mobile app |
| Database / ORM / migrations | **PostgreSQL** (Docker container) + SQLAlchemy 2.0 + Alembic | the same database option C would use |
| Frontend | **Vue 3 + TypeScript + Vite**, PWA | Pinia (state), Vue Router, Vitest (tests) |
| Tests | pytest, pytest-cov, hypothesis (property tests for the standings engine), httpx (API tests), Vitest (frontend), Playwright (E2E, later) | |
| Quality | ruff (lint + format), mypy, pre-commit | |
| CI/CD | GitHub Actions: lint → types → tests (+ coverage, Postgres as a service container) → Docker image build → frontend build → Pages deploy | |
| Local on Linux | **Docker Compose** + `Makefile`: `up`, `down`, `logs`, `test`, `lint`, `migrate`, `seed`, `export`, `preview` | see 5.1 |

### 5.1 Docker: local environment

Docker Compose starts the whole environment with one command, and doubles as a hands-on way to learn Docker:

| Service | Image | Role |
|---|---|---|
| `db` | official `postgres` (with a data volume) | database; data survives restarts |
| `api` | own `backend/Dockerfile` (multi-stage: uv installs dependencies, final image has the runtime only) | FastAPI with auto-reload (mounted `src/`) |
| `frontend` | `node` (Vite dev server) | UI preview with hot reload |
| `adminer` (optional) | `adminer` | browse the database in a browser |

Docker concepts covered along the way: Dockerfile and multi-stage builds, volumes, container networks, environment variables and `.env`, `healthcheck` (the API waits for the database), separate `compose.yaml` and `compose.override.yaml` for development.

Tests: the domain core runs without a database (fast, also outside Docker via `uv run pytest`); integration and API tests run against PostgreSQL, in a container locally (`make test`) and as a service container in GitHub Actions.

## 6. Repository layout

```
score_system/
├── backend/
│   ├── src/score_system/
│   │   ├── domain/         # models, rules engine, standings, fixtures (pure Python)
│   │   ├── application/    # services / use cases
│   │   ├── infrastructure/ # SQLAlchemy, repositories, static export
│   │   ├── api/            # FastAPI: v1 routers, schemas
│   │   └── cli.py          # e.g. `score export-static`, `score seed`
│   ├── presets/            # discipline rules in YAML
│   ├── migrations/         # Alembic
│   ├── Dockerfile
│   └── tests/              # unit / integration / api
├── frontend/               # Vue 3 + TypeScript + Vite (PWA), with its own Dockerfile
├── data/export/            # JSON snapshot published to Pages
├── docs/                   # this document and further docs
├── compose.yaml            # db, api, frontend
├── compose.override.yaml   # development settings (hot reload, ports)
├── .env.example
├── .github/workflows/      # ci.yml, pages.yml
├── Makefile
├── CLAUDE.md
└── README.md
```

## 7. Tests and CI from day one

- **Test pyramid:** many unit tests of the core (standings, tiebreakers, fixtures), integration tests of repositories against PostgreSQL, API tests via `httpx`/`TestClient`, a few Playwright E2E tests once there is a UI.
- **Property tests (hypothesis):** e.g. "total standings points equal the points awarded in matches", "round robin: every pair plays exactly once per round".
- **API contract tests:** an OpenAPI schema snapshot in the repo; CI flags unintended changes that would break the mobile app.
- **`ci.yml`** (every PR and push): backend: `uv sync` → `ruff check` → `ruff format --check` → `mypy` → `pytest --cov` with Postgres (coverage threshold, e.g. 85% for `domain/`); frontend: `npm ci` → lint → `vue-tsc` → Vitest → build; Docker: `docker compose build`.
- **`pages.yml`** (push to `main`): build the frontend with the `data/export/` snapshot → `actions/deploy-pages`.
- Local tests use the same command as CI (`make test`), so local results match CI.

## 8. Implementation stages

Each stage ends with a working, tested increment. Commits and pushes only with the owner's consent.

| # | Stage | Contents | Outcome |
|---|---|---|---|
| 0 | Foundation | repo structure, uv, ruff, mypy, pytest, pre-commit, `Makefile`, Docker Compose (`db` + `api` with a `/health` endpoint), Vue skeleton, `ci.yml` | `make up` works locally, CI green |
| 1 | Core: rules and standings | domain models, RuleSet + volleyball preset, `compute_standings` (3/2/1/0; points, set ratio, small-points ratio), tests (incl. hypothesis) | volleyball standings computed from a list of matches |
| 2 | Fixtures | round robin generator (single and double), match model and statuses, postponements/walkovers | generated, editable fixtures (in the core) |
| 3 | Persistence | SQLAlchemy + Alembic + Postgres in Docker, repositories, sample data (`make seed`) | data stored locally |
| 4 | API v1 | CRUD: disciplines, competitions, teams, rosters, players, matches, results, events; standings and statistics endpoints; OpenAPI snapshot | full API locally (Swagger UI) |
| 5 | Static export + Pages | `make export` → `data/export/`, `pages.yml`, publishing | public read-only site on GitHub Pages |
| 6 | Public frontend | standings, fixtures, teams, players, statistics; responsive | site for fans and players |
| 7 | Admin panel (local) | fixture editing, entering results and events, roster management | running the league without editing files |
| 8 | Extensions | groups + play-off, bracket, more presets (e.g. football), CSV import | tournaments, not only leagues |
| 9 | Mobile readiness | authentication (tokens), API versioning, generated client | ready for the mobile app |

## 9. Preparing for the mobile app

- All data through API v1 only (`/api/v1/...`), versioned, with stable identifiers (UUID or slug).
- Screen-oriented responses (e.g. standings with ready-made columns), with pagination and `updated_at` fields to ease caching and offline mode.
- Dates in UTC (ISO 8601) plus the league's time zone in configuration.
- Authentication planned as tokens (OAuth2/JWT) rather than cookie sessions, since tokens also work in mobile apps.
- Mobile-first web frontend shipped as a PWA, so part of the "mobile app" is available right away.

## 10. Risks and open questions

- **GDPR:** which player data is public (full name, date of birth, photo)? Plan a per-player "hide details" flag.
- **Live editing:** without a server, several people cannot enter results online; only option C solves that.
- **Complex regulations** (e.g. head-to-head mini-tables when three teams are tied) need careful testing, which is why the standings engine is the first, test-heavy stage.

## 11. Useful Claude Code skills

| Skill | Use in this project |
|---|---|
| `init` | generate and refresh `CLAUDE.md` |
| `update-config` | Claude Code hooks, e.g. run `make lint test` after edits or before finishing; command permissions |
| `session-start-hook` | startup script for cloud Claude sessions (install uv and dependencies) so tests and linters work immediately |
| `code-review` | review changes for bugs before a commit is approved |
| `simplify` | clean up code (duplication, excess complexity) after each stage |
| `security-review` | security review, important for the admin panel, API and authentication |
| `karpathy-guidelines` | guidelines against common LLM coding mistakes: small surgical changes, clear success criteria |
| `run` | launch the app and check a change working, not only in tests |
| `fewer-permission-prompts` | fewer permission prompts for safe commands (`pytest`, `ruff`) |
| `skill-creator` | create project skills, e.g. "add a discipline preset" or "add a tiebreaker" following the agreed pattern |
| `artifact-diagramming` | architecture and data model diagrams |
| `dataviz` | team and player statistics charts |

Also useful: plan mode before each stage, the `Plan` subagent for larger changes, and `/review` before a PR.

## 12. Decisions (made 2026-10-18)

- **D1.** Repository: `michbroniszewski/score_system`.
- **D2.** Hosting: option A, local editing with a read-only GitHub Pages site.
- **D3.** Backend: FastAPI.
- **D4.** Frontend: Vue 3 + TypeScript (PWA).
- **D5.** uv + Docker Compose (also to learn Docker).
- **D6.** First discipline: volleyball, round robin.
- **D7.** Database: PostgreSQL in Docker.
- **D8.** Volleyball scoring: 3:0 and 3:1 = 3 pts, 3:2 = 2 pts, 2:3 = 1 pt, 1:3 and 0:3 = 0 pts; tiebreakers: points, set ratio, small-points ratio (for now, may be extended later; revised 2026-10-18).
- **D9.** Project language: English for everything in the repository (code, identifiers, comments, docs, commits).
