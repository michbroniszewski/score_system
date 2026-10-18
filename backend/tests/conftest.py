"""Shared fixtures.

Database fixtures (`engine`, `session`): integration tests run against a real PostgreSQL in
a separate test database. Locally that is the Docker Compose `db` service (`make test`
starts it); in CI a service container. The schema is built by running the Alembic
migrations, so the migrations themselves are tested too. Tests that do not ask for a
database fixture never touch the database.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, make_url, text
from sqlalchemy.orm import Session

from score_system.domain.rules import RuleSet
from score_system.infrastructure.db import make_engine
from score_system.infrastructure.presets import load_ruleset

PRESETS = Path(__file__).parent.parent / "presets"


@pytest.fixture
def volleyball() -> RuleSet:
    return load_ruleset(PRESETS / "volleyball.yaml")


# Default: the Compose db service on its host port (DB_PORT in .env, exported by make).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+psycopg://score:score@localhost:{os.environ.get('DB_PORT') or 5432}"
    "/score_system_test",
)
BACKEND_DIR = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = make_url(TEST_DATABASE_URL)
    # The database is dropped and recreated: never do that to a non-test database.
    if not (url.database or "").endswith("_test"):
        raise RuntimeError(f"TEST_DATABASE_URL must name a *_test database, not {url.database!r}")
    admin = make_engine(url.set(database="postgres").render_as_string(hide_password=False))
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")

    engine = make_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def connection(engine: Engine) -> Iterator[Connection]:
    """A connection in a transaction that is rolled back after the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    """A session whose changes are rolled back after the test.

    Its commits only release savepoints inside the test's transaction.
    """
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        yield session
