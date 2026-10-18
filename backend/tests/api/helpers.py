"""Helpers shared by the API tests."""

from typing import Any

from fastapi.testclient import TestClient

API = "/api/v1"
STRAIGHT_WIN = {"sets": [{"home": 25, "away": 20}] * 3}


def post(client: TestClient, path: str, body: Any = None, expect: int = 200) -> Any:
    response = client.post(API + path, json=body)
    assert response.status_code == expect, response.text
    return response.json()


def get(client: TestClient, path: str, expect: int = 200) -> Any:
    response = client.get(API + path)
    assert response.status_code == expect, response.text
    return response.json()
