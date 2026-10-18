from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from score_system.api.deps import get_repo
from score_system.api.main import app
from score_system.infrastructure.repository import Repository


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """API client on the rolled-back test session instead of the real database."""
    app.dependency_overrides[get_repo] = lambda: Repository(session)
    yield TestClient(app)
    app.dependency_overrides.clear()
