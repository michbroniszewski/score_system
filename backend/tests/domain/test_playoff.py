from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from score_system.domain.errors import DomainError
from score_system.domain.models import Match, MatchStatus, SetScore
from score_system.domain.playoff import (
    PlayoffFormat,
    Series,
    final_places,
    games_to_add,
    series_states,
    surplus_games,
)
from score_system.infrastructure.presets import load_playoff_file
from tests.conftest import PRESETS

TAURON = load_playoff_file(PRESETS / "playoffs" / "tauron-liga.yaml")
TABLE = [f"T{place}" for place in range(1, 15)]  # regular-season order, 14 teams

Games = dict[str, list[Match]]


def won_by(game: Match, winner: str) -> Match:
    sets = (SetScore(25, 20),) * 3 if winner == game.home else (SetScore(20, 25),) * 3
    return replace(game, status=MatchStatus.PLAYED, sets=sets)


def play(games: Games, winners: Mapping[str, str]) -> Games:
    """Add the games the play-off needs and let `winners[series]` win them, until no
    series with a known winner needs another game."""
    games = {key: list(gs) for key, gs in games.items()}
    while True:
        states = series_states(TAURON, TABLE, games)
        pending = [g for g in games_to_add(states, games) if g.series in winners]
        if not pending:
            return games
        for game in pending:
            assert game.series is not None
            games.setdefault(game.series, []).append(won_by(game, winners[game.series]))


def test_tauron_format_loads() -> None:
    assert TAURON.seeds == 8
    assert {key: s.wins for key, s in TAURON.series.items()} == {
        "A": 2, "B": 2, "C": 2, "D": 2, "E": 2, "F": 2, "I": 2, "J": 3, "L": 3,
    }  # fmt: skip


def test_quarter_finals_pair_the_table() -> None:
    states = series_states(TAURON, TABLE, {})

    assert [(s.high, s.low) for s in map(states.get, "ABCD") if s] == [
        ("T1", "T8"),
        ("T2", "T7"),
        ("T3", "T6"),
        ("T4", "T5"),
    ]
    assert states["E"] == Series("E", 2)  # waits for A and D


def test_series_start_with_the_games_the_leader_needs() -> None:
    states = series_states(TAURON, TABLE, {})

    added = games_to_add(states, {})

    assert [(g.series, g.round, g.home, g.away) for g in added if g.series == "A"] == [
        ("A", 1, "T1", "T8"),  # the better-seeded team hosts game 1,
        ("A", 2, "T8", "T1"),  # then the host alternates
    ]
    assert len(added) == 8


def test_third_game_only_at_one_all() -> None:
    first, second = (g for g in games_to_add(series_states(TAURON, TABLE, {}), {})[:2])
    one_all: Games = {"A": [won_by(first, "T1"), won_by(second, "T8")]}
    two_nil: Games = {"A": [won_by(first, "T1"), won_by(second, "T1")]}

    third = games_to_add(series_states(TAURON, TABLE, one_all), one_all)
    after_win = games_to_add(series_states(TAURON, TABLE, two_nil), two_nil)

    assert [(g.series, g.round, g.home) for g in third if g.series == "A"] == [("A", 3, "T1")]
    assert [g for g in after_win if g.series == "A"] == []
    assert series_states(TAURON, TABLE, two_nil)["A"].winner == "T1"


def test_whole_play_off_and_final_classification() -> None:
    # Upsets: T7 beats T2, T5 beats T4; T5 beats T1 in the semi-final.
    winners = {"A": "T1", "B": "T7", "C": "T3", "D": "T5"}
    games = play({}, winners)
    states = series_states(TAURON, TABLE, games)
    assert (states["E"].high, states["E"].low) == ("T1", "T5")
    assert (states["F"].high, states["F"].low) == ("T3", "T7")  # T3 is better seeded
    # Places 5-6: the two best-seeded quarter-final losers; T6 and T8 are 7th and 8th.
    assert (states["I"].high, states["I"].low, states["I"].rest) == ("T2", "T4", ("T6", "T8"))

    games = play(games, {**winners, "E": "T5", "F": "T3", "I": "T4", "J": "T1", "L": "T3"})
    states = series_states(TAURON, TABLE, games)

    assert len(games["L"]) == 3 and games["L"][0].home == "T3"  # best of five, 3:0
    assert final_places(TAURON, TABLE, states) == [
        "T3", "T5", "T1", "T7", "T4", "T2", "T6", "T8",
        "T9", "T10", "T11", "T12", "T13", "T14",
    ]  # fmt: skip


def test_places_are_unknown_until_decided() -> None:
    places = final_places(TAURON, TABLE, series_states(TAURON, TABLE, {}))

    assert places[:8] == [None] * 8
    assert places[8:] == TABLE[8:]


def test_surplus_games_after_a_corrected_result() -> None:
    first, second = (g for g in games_to_add(series_states(TAURON, TABLE, {}), {})[:2])
    third = Match(3, "T1", "T8", series="A")
    # At 1:1 game 3 was added; then game 2 was corrected to a T1 win: 2:0.
    games: Games = {"A": [won_by(first, "T1"), won_by(second, "T1"), third]}

    states = series_states(TAURON, TABLE, games)

    assert surplus_games(states, games) == [third]
    assert surplus_games(states, {"A": games["A"][:2]}) == []


def test_walkover_wins_a_game() -> None:
    first, second = (g for g in games_to_add(series_states(TAURON, TABLE, {}), {})[:2])
    games: Games = {
        "A": [
            replace(g, status=MatchStatus.WALKOVER, walkover_winner="T8") for g in (first, second)
        ]
    }

    assert series_states(TAURON, TABLE, games)["A"].winner == "T8"


@pytest.mark.parametrize(
    ("games", "message"),
    [
        ({"A": [Match(1, "T1", "T2")]}, "not between"),
        ({"A": [won_by(Match(n, "T1", "T8"), "T1") for n in (1, 2, 3)]}, "after it was decided"),
    ],
)
def test_inconsistent_games_are_rejected(games: Games, message: str) -> None:
    with pytest.raises(DomainError, match=message):
        series_states(TAURON, TABLE, games)


def test_needs_enough_teams() -> None:
    with pytest.raises(DomainError, match="needs 8 teams"):
        series_states(TAURON, TABLE[:7], {})


VALID: dict[str, Any] = {
    "name": "Final four",
    "seeds": 4,
    "series": {
        "S1": {"sides": ["seed 1", "seed 4"], "wins": 1},
        "S2": {"sides": ["seed 2", "seed 3"], "wins": 1},
        "F": {"sides": ["winner S1", "winner S2"], "wins": 1},
    },
    "places": ["winner F", "loser F", "loser S1", "loser S2"],
}


def test_a_simple_format_is_valid() -> None:
    assert PlayoffFormat.model_validate(VALID).seeds == 4


@pytest.mark.parametrize(
    "change",
    [
        {"seeds": 5},  # seed 5 starts no series
        {"series": {**VALID["series"], "S2": {"sides": ["seed 2", "seed 2"], "wins": 1}}},
        {"series": {"F": VALID["series"]["F"], **VALID["series"]}},  # uses later series
        {"series": {**VALID["series"], "F": {"sides": ["winner S1"], "wins": 1}}},
        {"series": {**VALID["series"], "F": {"sides": ["best S1", "winner S2"], "wins": 1}}},
        {"places": ["winner F", "loser F", "loser S1", "loser S1"]},  # used twice
        {"places": ["winner F", "loser F", "loser S1", "winner S2"]},  # S2's winner plays on
        {"places": ["winner F", "loser F", "loser S1"]},  # a place missing
        {"places": ["winner F", "loser F", "loser S1", "rest F"]},  # F has no rest
    ],
)
def test_invalid_format_is_rejected(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PlayoffFormat.model_validate({**VALID, **change})


def test_every_format_file_is_valid() -> None:
    for path in (PRESETS / "playoffs").glob("*.yaml"):
        PlayoffFormat.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
