"""The OpenAPI schema is the contract with every client (web, mobile).

A failure here means the API changed. If the change is intended, regenerate the
snapshot with `make openapi` and commit it together with the change.
"""

from pathlib import Path

from score_system.cli import openapi_json

SNAPSHOT = Path(__file__).parents[2] / "openapi.json"


def test_openapi_matches_snapshot() -> None:
    assert openapi_json() == SNAPSHOT.read_text(encoding="utf-8")
