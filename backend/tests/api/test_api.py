from typing import Any

import pytest
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


@pytest.fixture
def league(client: TestClient) -> list[dict[str, Any]]:
    """A volleyball league with four entered teams and generated fixtures."""
    post(client, "/competitions", {"slug": "league", "name": "League", "preset": "volleyball"}, 201)
    for name in ["Owls", "Eagles", "Hawks", "Ravens"]:
        post(client, "/competitions/league/teams", {"team": {"name": name}}, 201)
    matches: list[dict[str, Any]] = post(client, "/competitions/league/fixtures", {}, 201)
    return matches


def test_presets(client: TestClient) -> None:
    assert get(client, "/presets") == ["volleyball"]


def test_competition_validation(client: TestClient) -> None:
    body = {"slug": "league", "name": "League", "preset": "volleyball"}
    stored = {**body, "timezone": "Europe/Warsaw"}
    assert post(client, "/competitions", body, 201) == stored
    post(client, "/competitions", body, 409)
    post(client, "/competitions", {**body, "slug": "cup", "preset": "chess"}, 422)
    post(client, "/competitions", {**body, "slug": "Not a slug"}, 422)
    for timezone in ["Mars/Olympus", "../etc", ""]:
        post(client, "/competitions", {**body, "slug": "cup", "timezone": timezone}, 422)
    cup = {**body, "slug": "cup", "name": "Cup", "timezone": "UTC"}
    assert post(client, "/competitions", cup, 201) == cup
    assert get(client, "/competitions") == [cup, stored]
    get(client, "/competitions/missing", 404)


def test_saved_teams_form_the_general_base(client: TestClient) -> None:
    post(client, "/competitions", {"slug": "cup", "name": "Cup", "preset": "volleyball"}, 201)
    saved = post(client, "/teams", {"name": "Eagles", "saved": True}, 201)
    one_off = post(client, "/competitions/cup/teams", {"team": {"name": "Guests"}}, 201)
    post(client, "/competitions/cup/teams", {"team_id": saved["id"]}, 201)

    assert [t["name"] for t in get(client, "/teams")] == ["Eagles"]
    assert [t["name"] for t in get(client, "/competitions/cup/teams")] == ["Eagles", "Guests"]

    response = client.patch(f"{API}/teams/{one_off['id']}", json={"saved": True})
    assert response.status_code == 200 and response.json()["saved"] is True
    assert [t["name"] for t in get(client, "/teams")] == ["Eagles", "Guests"]


def test_team_rules(client: TestClient) -> None:
    post(client, "/competitions", {"slug": "cup", "name": "Cup", "preset": "volleyball"}, 201)
    team = post(client, "/teams", {"name": "Eagles"}, 201)

    post(client, "/teams", {"name": "Eagles"}, 409)
    post(client, "/competitions/cup/teams", {"team_id": team["id"]}, 201)
    post(client, "/competitions/cup/teams", {"team_id": team["id"]}, 409)
    post(client, "/competitions/cup/teams", {}, 422)  # neither team_id nor team
    get(client, "/teams/00000000-0000-0000-0000-000000000000", 404)
    assert client.patch(f"{API}/teams/{team['id']}", json={"name": "Eagles"}).status_code == 200


def test_club_with_several_teams(client: TestClient) -> None:
    club = post(client, "/clubs", {"name": "Eagles VC"}, 201)
    for name in ["Eagles", "Eagles II"]:
        post(client, "/teams", {"name": name, "club_id": club["id"], "saved": True}, 201)

    detail = get(client, f"/clubs/{club['id']}")
    assert [t["name"] for t in detail["teams"]] == ["Eagles", "Eagles II"]
    assert get(client, "/clubs") == [club]
    post(client, "/clubs", {"name": "Eagles VC"}, 409)
    post(client, "/teams", {"name": "X", "club_id": "00000000-0000-0000-0000-000000000000"}, 404)


def test_fixtures(client: TestClient, league: list[dict[str, Any]]) -> None:
    assert len(league) == 6
    assert {m["status"] for m in league} == {"scheduled"}
    assert get(client, "/competitions/league/matches") == league
    post(client, "/competitions/league/fixtures", {}, 409)
    post(client, "/competitions/league/teams", {"team": {"name": "Late"}}, 409)


def test_match_lifecycle(client: TestClient, league: list[dict[str, Any]]) -> None:
    first, second, third = (m["id"] for m in league[:3])

    moved = post(client, f"/matches/{first}/reschedule", {"starts_at": "2026-11-06T20:00:00+01:00"})
    assert moved["starts_at"] == "2026-11-06T19:00:00Z"
    post(client, f"/matches/{first}/reschedule", {"starts_at": "2026-11-06T20:00:00"}, 422)
    assert post(client, f"/matches/{first}/postpone")["status"] == "postponed"

    played = post(client, f"/matches/{first}/result", STRAIGHT_WIN)
    assert played["status"] == "played" and len(played["sets"]) == 3
    post(client, f"/matches/{first}/result", {"sets": [{"home": 25, "away": 20}]}, 422)
    post(client, f"/matches/{first}/cancel", None, 409)

    winner = league[1]["away"]["id"]
    walkover = post(client, f"/matches/{second}/walkover", {"winner": winner})
    assert (walkover["status"], walkover["walkover_winner"]) == ("walkover", winner)
    assert post(client, f"/matches/{third}/cancel")["status"] == "cancelled"
    assert get(client, f"/matches/{first}") == played
    get(client, "/matches/00000000-0000-0000-0000-000000000000", 404)


def test_standings(client: TestClient, league: list[dict[str, Any]]) -> None:
    first = league[0]
    post(client, f"/matches/{first['id']}/result", STRAIGHT_WIN)

    table = get(client, "/competitions/league/standings")

    assert [row["position"] for row in table] == [1, 2, 3, 4]
    leader = table[0]
    assert leader["team"] == first["home"]
    assert (leader["points"], leader["sets_won"], leader["small_points_won"]) == (3, 3, 75)
    assert sum(row["played"] for row in table) == 2
