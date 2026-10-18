from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import sessionmaker

from score_system.api import deps
from score_system.api.main import app


@pytest.fixture
def client(connection: Connection, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """API client on the test's rolled-back transaction instead of the real database.

    The real `get_repo` runs, so each request commits or rolls back its own savepoint
    just as it would commit or roll back its transaction.
    """
    sessions = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    monkeypatch.setattr(deps, "_sessions", lambda: sessions)
    yield TestClient(app)
