from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import API, STRAIGHT_WIN, get, post


@pytest.fixture
def league(client: TestClient) -> dict[str, Any]:
    """Two teams with fixtures; the only match is played."""
    post(client, "/competitions", {"slug": "league", "name": "League", "preset": "volleyball"}, 201)
    home = post(client, "/competitions/league/teams", {"team": {"name": "Eagles"}}, 201)
    away = post(client, "/competitions/league/teams", {"team": {"name": "Owls"}}, 201)
    (match,) = post(client, "/competitions/league/fixtures", {}, 201)
    post(client, f"/matches/{match['id']}/result", STRAIGHT_WIN)
    return {
        "home": match["home"]["id"],
        "away": match["away"]["id"],
        "match": match["id"],
        "teams": {home["name"]: home["id"], away["name"]: away["id"]},
    }


def roster_path(team_id: str) -> str:
    return f"/competitions/league/teams/{team_id}/roster"


def test_player_crud(client: TestClient) -> None:
    player = post(client, "/players", {"first_name": "Anna", "last_name": "Nowak"}, 201)
    response = client.patch(f"{API}/players/{player['id']}", json={"last_name": "Kowalska"})

    assert response.json() == {**player, "last_name": "Kowalska"}
    assert get(client, f"/players/{player['id']}")["last_name"] == "Kowalska"
    get(client, "/players/00000000-0000-0000-0000-000000000000", 404)


def test_roster_keeps_history(client: TestClient, league: dict[str, Any]) -> None:
    eagles, owls = league["teams"]["Eagles"], league["teams"]["Owls"]
    body = {
        "player": {"first_name": "Anna", "last_name": "Nowak"},
        "number": 7,
        "position": "setter",
        "joined_on": "2026-09-01",
    }
    entry = post(client, roster_path(eagles), body, 201)
    player_id = entry["player"]["id"]

    # Still in the Eagles roster: cannot join another team of the same competition.
    post(client, roster_path(owls), {"player_id": player_id}, 409)
    post(client, f"/roster-entries/{entry['id']}/leave", {"left_on": "2026-08-01"}, 422)
    left = post(client, f"/roster-entries/{entry['id']}/leave", {"left_on": "2026-12-31"})
    post(client, f"/roster-entries/{entry['id']}/leave", {"left_on": "2026-12-31"}, 409)
    # A returning player needs a date, otherwise the entries could overlap.
    post(client, roster_path(owls), {"player_id": player_id, "number": 10}, 422)
    rejoin = {"player_id": player_id, "number": 10, "joined_on": "2026-12-31"}
    post(client, roster_path(owls), rejoin, 201)

    assert left["left_on"] == "2026-12-31"
    assert get(client, roster_path(eagles)) == [left]
    assert [e["number"] for e in get(client, roster_path(owls))] == [10]
    # The whole competition at once (the admin panel offers free players from it).
    assert [e["team_id"] for e in get(client, "/competitions/league/roster")] == [eagles, owls]


def test_roster_rules(client: TestClient, league: dict[str, Any]) -> None:
    outsider = post(client, "/teams", {"name": "Outsiders"}, 201)

    post(
        client, roster_path(outsider["id"]), {"player": {"first_name": "A", "last_name": "B"}}, 404
    )
    post(client, roster_path(league["home"]), {}, 422)


def test_events_and_stats(client: TestClient, league: dict[str, Any]) -> None:
    def join(team: str, first: str, last: str) -> str:
        body = {"player": {"first_name": first, "last_name": last}}
        entry = post(client, roster_path(team), body, 201)
        player_id: str = entry["player"]["id"]
        return player_id

    anna = join(league["home"], "Anna", "Nowak")
    ola = join(league["away"], "Ola", "Kowal")
    events = f"/matches/{league['match']}/events"

    post(
        client,
        events,
        {"team_id": league["home"], "player_id": anna, "stat": "aces", "value": 2},
        201,
    )
    post(client, events, {"team_id": league["home"], "player_id": anna, "stat": "aces"}, 201)
    mvp = post(client, events, {"team_id": league["away"], "player_id": ola, "stat": "mvp"}, 201)
    # Wrong statistic, a player outside the team's roster, a value below one.
    post(client, events, {"team_id": league["home"], "player_id": anna, "stat": "goals"}, 422)
    post(client, events, {"team_id": league["home"], "player_id": ola, "stat": "aces"}, 422)
    post(
        client,
        events,
        {"team_id": league["home"], "player_id": anna, "stat": "aces", "value": 0},
        422,
    )

    assert len(get(client, events)) == 3
    stats = get(client, "/competitions/league/stats")
    assert [
        (s["player"]["name"], s["team"]["name"], s["stats"]["aces"], s["stats"]["mvp"])
        for s in stats
    ] == [
        ("Ola Kowal", "Owls", 0, 1),
        ("Anna Nowak", "Eagles", 3, 0),
    ]

    assert client.delete(f"{API}/events/{mvp['id']}").status_code == 204
    assert client.delete(f"{API}/events/{mvp['id']}").status_code == 404
    assert [s["player"]["name"] for s in get(client, "/competitions/league/stats")] == [
        "Anna Nowak"
    ]


def test_events_need_a_played_match(client: TestClient) -> None:
    post(client, "/competitions", {"slug": "cup", "name": "Cup", "preset": "volleyball"}, 201)
    team = post(client, "/competitions/cup/teams", {"team": {"name": "A"}}, 201)
    post(client, "/competitions/cup/teams", {"team": {"name": "B"}}, 201)
    (match,) = post(client, "/competitions/cup/fixtures", {}, 201)
    entry = post(
        client,
        f"/competitions/cup/teams/{team['id']}/roster",
        {"player": {"first_name": "A", "last_name": "B"}},
        201,
    )

    body = {"team_id": team["id"], "player_id": entry["player"]["id"], "stat": "aces"}
    post(client, f"/matches/{match['id']}/events", body, 409)
