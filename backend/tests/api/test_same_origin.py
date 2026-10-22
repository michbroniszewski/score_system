from fastapi.testclient import TestClient

from score_system.api.main import app
from tests.api.helpers import API


def test_changes_from_another_site_are_refused() -> None:
    # Refused before any route runs, so no database is needed.
    client = TestClient(app)  # sends Host: testserver
    for origin in ["https://evil.example", "http://testserver.evil.example", "null"]:
        response = client.post(f"{API}/competitions", json={}, headers={"Origin": origin})
        assert response.status_code == 403, origin


def test_same_origin_and_origin_less_changes_pass(client: TestClient) -> None:
    body = {"slug": "league", "name": "League", "preset": "volleyball"}
    headers = {"Origin": "http://testserver"}

    assert client.post(f"{API}/competitions", json=body, headers=headers).status_code == 201
    # Through the Vite dev server, which proxies /api and names itself in X-Forwarded-Host.
    proxied = {"Origin": "http://localhost:5173", "X-Forwarded-Host": "localhost:5173"}
    assert client.post(f"{API}/competitions", json=body, headers=proxied).status_code == 409
    assert client.post(f"{API}/competitions", json=body).status_code == 409  # reached the route
    # Reading stays open to any site.
    assert client.get(f"{API}/presets", headers={"Origin": "https://evil.example"}).is_success
