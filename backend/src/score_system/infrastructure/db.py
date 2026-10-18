import os

from sqlalchemy import Engine, create_engine

# Matches compose.yaml defaults; inside Docker Compose, DATABASE_URL points at host "db".
DEFAULT_DATABASE_URL = "postgresql+psycopg://score:score@localhost:5432/score_system"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url())
