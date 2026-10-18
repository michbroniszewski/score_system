from collections.abc import Iterator
from functools import cache

from sqlalchemy.orm import Session, sessionmaker

from score_system.infrastructure.db import make_engine
from score_system.infrastructure.repository import Repository


@cache
def _sessions() -> sessionmaker[Session]:
    return sessionmaker(make_engine())


def get_repo() -> Iterator[Repository]:
    """One transaction per request: committed on success, rolled back on error."""
    with _sessions().begin() as session:
        yield Repository(session)
