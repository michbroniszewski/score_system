"""Regression tests for issues found in the stage 4 code review."""

from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from score_system.api.main import app
from score_system.infrastructure.repository import Repository
from tests.api.test_api import API, STRAIGHT_WIN, get, post


@pytest.fixture
def match(client: TestClient) -> dict[str, Any]:
    """A two-team league with its only match scheduled on 2026-11-06."""
    post(client, "/competitions", {"slug": "league", "name": "League", "preset": "volleyball"}, 201)
    for name in ["Eagles", "Owls"]:
        post(client, "/competitions/league/teams", {"team": {"name": name}}, 201)
    (fixture,) = post(client, "/competitions/league/fixtures", {}, 201)
    body = {"starts_at": "2026-11-06T19:00:00Z"}
    scheduled: dict[str, Any] = post(client, f"/matches/{fixture['id']}/reschedule", body)
    return scheduled


def join(client: TestClient, team_id: str, body: dict[str, Any], expect: int = 201) -> Any:
    return post(client, f"/competitions/league/teams/{team_id}/roster", body, expect)


def new_player(last_name: str, **fields: Any) -> dict[str, Any]:
    return {"player": {"first_name": "P", "last_name": last_name}, **fields}


def test_stats_ignore_a_result_corrected_to_walkover(
    client: TestClient, match: dict[str, Any]
) -> None:
    home = match["home"]["id"]
    player = join(client, home, new_player("Nowak"))["player"]["id"]
    post(client, f"/matches/{match['id']}/result", STRAIGHT_WIN)
    event = {"team_id": home, "player_id": player, "stat": "aces"}
    post(client, f"/matches/{match['id']}/events", event, 201)
    assert len(get(client, "/competitions/league/stats")) == 1

    post(client, f"/matches/{match['id']}/walkover", {"winner": home})

    assert get(client, "/competitions/league/stats") == []


def test_stats_skip_statistics_no_longer_in_the_preset(
    client: TestClient, session: Session, match: dict[str, Any]
) -> None:
    home = match["home"]["id"]
    player = join(client, home, new_player("Nowak"))["player"]["id"]
    post(client, f"/matches/{match['id']}/result", STRAIGHT_WIN)
    Repository(session).add_event(UUID(match["id"]), UUID(home), UUID(player), "removed", 1)

    assert get(client, "/competitions/league/stats") == []


def test_patch_can_clear_club_and_short_name(client: TestClient) -> None:
    club = post(client, "/clubs", {"name": "Eagles VC"}, 201)
    team = post(
        client, "/teams", {"name": "Eagles", "short_name": "EAG", "club_id": club["id"]}, 201
    )

    response = client.patch(f"{API}/teams/{team['id']}", json={"club_id": None, "short_name": None})

    assert response.status_code == 200
    assert (response.json()["club_id"], response.json()["short_name"]) == (None, None)
    for body in [{"name": None}, {"saved": None}]:
        assert client.patch(f"{API}/teams/{team['id']}", json=body).status_code == 422
    player = post(client, "/players", {"first_name": "A", "last_name": "B"}, 201)
    assert (
        client.patch(f"{API}/players/{player['id']}", json={"last_name": None}).status_code == 422
    )


def test_event_needs_the_player_in_the_roster_on_match_day(
    client: TestClient, match: dict[str, Any]
) -> None:
    home = match["home"]["id"]
    entry = join(client, home, new_player("Left", joined_on="2026-09-01"))
    post(client, f"/roster-entries/{entry['id']}/leave", {"left_on": "2026-10-01"})
    current = join(client, home, new_player("Current", joined_on="2026-10-02"))
    post(client, f"/matches/{match['id']}/result", STRAIGHT_WIN)
    events = f"/matches/{match['id']}/events"

    left = {"team_id": home, "player_id": entry["player"]["id"], "stat": "aces"}
    post(client, events, left, 422)
    post(client, events, {**left, "player_id": current["player"]["id"]}, 201)


def test_rejoining_cannot_overlap_the_previous_roster(
    client: TestClient, match: dict[str, Any]
) -> None:
    home, away = match["home"]["id"], match["away"]["id"]
    entry = join(client, home, new_player("Nowak", joined_on="2026-09-01"))
    post(client, f"/roster-entries/{entry['id']}/leave", {"left_on": "2026-11-10"})
    player_id = entry["player"]["id"]

    join(client, away, {"player_id": player_id, "joined_on": "2026-11-01"}, 422)
    join(client, away, {"player_id": player_id, "joined_on": "2026-11-10"}, 201)


def test_roster_of_a_team_outside_the_competition_is_not_found(
    client: TestClient, match: dict[str, Any]
) -> None:
    outsider = post(client, "/teams", {"name": "Outsiders"}, 201)

    get(client, f"/competitions/league/teams/{outsider['id']}/roster", 404)


def handle(exc: Exception) -> tuple[int, Any]:
    """Status and body the API's error handlers give for `exc` raised in a route."""
    probe = FastAPI()
    for exc_type, handler in app.exception_handlers.items():
        probe.add_exception_handler(exc_type, handler)

    @probe.get("/")
    def fail() -> None:
        raise exc

    response = TestClient(probe, raise_server_exceptions=False).get("/")
    return response.status_code, response.json()


def test_internal_validation_error_is_a_server_error() -> None:
    class Model(BaseModel):
        number: int

    with pytest.raises(ValidationError) as error:
        Model.model_validate({"number": "x"})

    assert handle(error.value) == (500, {"detail": "internal error"})


def test_unique_violation_is_a_conflict() -> None:
    error = IntegrityError("INSERT ...", {}, Exception("duplicate key"))

    assert handle(error) == (409, {"detail": "conflicts with existing data"})
