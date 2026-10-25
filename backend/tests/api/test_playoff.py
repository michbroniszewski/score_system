import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from score_system.api.export import export
from score_system.infrastructure.repository import Repository
from tests.api.helpers import STRAIGHT_WIN, get, post

LOST = {"sets": [{"home": 20, "away": 25}] * 3}
TEAMS = [f"T{i}" for i in range(1, 10)]  # T1 wins all its matches, T9 loses all


def season(client: TestClient, playoff: str | None = "tauron-liga") -> dict[str, str]:
    """A competition of 9 teams whose regular season is played but for one match: the
    better-numbered team always wins, so the table is T1..T9. Returns team ids by name."""
    body = {"slug": "liga", "name": "Liga", "preset": "volleyball", "playoff": playoff}
    post(client, "/competitions", body, 201)
    ids = {
        name: post(client, "/competitions/liga/teams", {"team": {"name": name}}, 201)["id"]
        for name in TEAMS
    }
    rank = {team_id: i for i, team_id in enumerate(ids.values())}
    *played, last = post(client, "/competitions/liga/fixtures", {}, 201)
    for match in played:
        home_wins = rank[match["home"]["id"]] < rank[match["away"]["id"]]
        post(client, f"/matches/{match['id']}/result", STRAIGHT_WIN if home_wins else LOST)
    post(client, "/competitions/liga/playoff", None, 409)  # one match left
    home_wins = rank[last["home"]["id"]] < rank[last["away"]["id"]]
    post(client, f"/matches/{last['id']}/result", STRAIGHT_WIN if home_wins else LOST)
    return ids


def series(playoff: dict[str, Any], key: str) -> dict[str, Any]:
    return next(s for s in playoff["series"] if s["key"] == key)


def win(client: TestClient, key: str, winner: str) -> dict[str, Any]:
    """Let `winner` win the series' open games until it is decided."""
    while True:
        current = series(get(client, "/competitions/liga/playoff"), key)
        if current["winner"] is not None:
            return current
        game = next(m for m in current["matches"] if m["status"] == "scheduled")
        result = STRAIGHT_WIN if game["home"]["name"] == winner else LOST
        post(client, f"/matches/{game['id']}/result", result)


def test_formats_are_listed(client: TestClient) -> None:
    assert get(client, "/playoffs") == ["tauron-liga"]
    tauron = get(client, "/playoffs/tauron-liga")
    assert (tauron["seeds"], tauron["series"][0]) == (
        8,
        {"key": "A", "sides": ["seed 1", "seed 8"], "wins": 2},
    )
    get(client, "/playoffs/nba", 404)


def test_competition_keeps_its_format(client: TestClient) -> None:
    body = {"slug": "x", "name": "X", "preset": "volleyball"}
    assert post(client, "/competitions", body, 201)["playoff"] is None
    post(client, "/competitions", {**body, "slug": "y", "playoff": "nba"}, 422)
    get(client, "/competitions/x/playoff", 404)


def test_start_pairs_the_table_and_schedules_two_games(client: TestClient) -> None:
    season(client)
    before = get(client, "/competitions/liga/playoff")
    assert (before["started"], series(before, "A")["home"], before["places"]) == (False, None, [])

    started = post(client, "/competitions/liga/playoff", None, 201)

    pairs = [(s["home"]["name"], s["away"]["name"]) for s in started["series"][:4]]
    assert pairs == [("T1", "T8"), ("T2", "T7"), ("T3", "T6"), ("T4", "T5")]
    games = series(started, "A")["matches"]
    assert [(g["series"], g["round"], g["home"]["name"]) for g in games] == [
        ("A", 1, "T1"),
        ("A", 2, "T8"),
    ]
    assert (series(started, "E")["home"], series(started, "E")["sides"]) == (
        None,
        ["winner A", "winner D"],
    )
    post(client, "/competitions/liga/playoff", None, 409)  # only once
    # Play-off games are not season matches and do not change the table.
    assert all(m["series"] is None for m in get(client, "/competitions/liga/matches"))
    assert get(client, "/competitions/liga/standings")[0]["played"] == 8


def test_third_game_comes_and_goes_with_the_result(client: TestClient) -> None:
    season(client)
    first, second = series(post(client, "/competitions/liga/playoff", None, 201), "A")["matches"]
    post(client, f"/matches/{first['id']}/result", STRAIGHT_WIN)  # T1 hosts and wins
    post(client, f"/matches/{second['id']}/result", STRAIGHT_WIN)  # T8 hosts and wins: 1:1

    one_all = series(get(client, "/competitions/liga/playoff"), "A")
    assert [(g["round"], g["home"]["name"]) for g in one_all["matches"]][2:] == [(3, "T1")]

    post(client, f"/matches/{second['id']}/result", LOST)  # corrected: T1 won game 2 too
    decided = series(get(client, "/competitions/liga/playoff"), "A")
    assert (len(decided["matches"]), decided["winner"]["name"]) == (2, "T1")


def test_whole_play_off_gives_the_final_classification(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    season(client)
    post(client, "/competitions/liga/playoff", None, 201)
    for key, winner in {"A": "T1", "B": "T7", "C": "T3", "D": "T5"}.items():
        win(client, key, winner)
    for key, winner in {"E": "T5", "F": "T3", "I": "T4", "J": "T1", "L": "T3"}.items():
        win(client, key, winner)

    playoff = get(client, "/competitions/liga/playoff")

    assert len(series(playoff, "L")["matches"]) == 3  # best of five won 3:0
    assert [p["team"]["name"] for p in playoff["places"]] == [
        "T3", "T5", "T1", "T7", "T4", "T2", "T6", "T8", "T9",
    ]  # fmt: skip
    # The static export carries the play-off and its games.
    export(Repository(session), tmp_path)
    root = tmp_path / "api" / "v1"
    exported = json.loads((root / "competitions" / "liga" / "playoff.json").read_text())
    assert exported == playoff
    game = series(playoff, "L")["matches"][0]
    assert (root / "matches" / f"{game['id']}.json").exists()


def test_a_season_correction_cannot_contradict_the_play_off(client: TestClient) -> None:
    ids = season(client)
    post(client, "/competitions/liga/playoff", None, 201)
    win(client, "A", "T1")
    # T9 beating T8 would make T9 the 8th seed, but T1-T8 has already been played.
    (match,) = (
        m
        for m in get(client, "/competitions/liga/matches")
        if {m["home"]["id"], m["away"]["id"]} == {ids["T8"], ids["T9"]}
    )
    t9_wins = STRAIGHT_WIN if match["home"]["id"] == ids["T9"] else LOST

    post(client, f"/matches/{match['id']}/result", t9_wins, 422)

    assert get(client, "/competitions/liga/standings")[7]["team"]["name"] == "T8"
    assert series(get(client, "/competitions/liga/playoff"), "A")["winner"]["name"] == "T1"


def test_no_play_off_without_a_format(client: TestClient) -> None:
    post(client, "/competitions", {"slug": "liga", "name": "Liga", "preset": "volleyball"}, 201)
    post(client, "/competitions/liga/playoff", None, 404)
