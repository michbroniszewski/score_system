# Multi-stage build: the "builder" stage installs dependencies with uv,
# the final "runtime" stage copies only the ready virtualenv and source code.

# --- Stage 1: builder -------------------------------------------------------
FROM python:3.12-slim AS builder

# Copy the uv binary from its official image instead of installing it with pip.
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# Compile .pyc files at install time (faster start) and copy files instead of
# hard-linking them (the cache and the target live on different filesystems).
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first, in a separate layer. This layer is rebuilt only
# when pyproject.toml or uv.lock change, not on every source code change.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Now copy the source and install the project itself, plus the files it reads at
# runtime: discipline presets and database migrations.
COPY src ./src
RUN uv sync --locked --no-dev
COPY presets ./presets
COPY alembic.ini ./
COPY migrations ./migrations

# --- Stage 2: runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime

# Run as an unprivileged user rather than root.
RUN useradd --create-home app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
USER app

# Put the virtualenv first on PATH, so "uvicorn" means the installed one.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "score_system.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
