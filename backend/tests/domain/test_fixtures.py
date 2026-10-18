from collections import Counter

import pytest
from hypothesis import given
from hypothesis import strategies as st

from score_system.domain.fixtures import round_robin
from score_system.domain.models import Match, MatchStatus


def teams(n: int) -> list[str]:
    return [f"T{i}" for i in range(n)]


def test_four_teams_single() -> None:
    matches = round_robin(["A", "B", "C", "D"])

    assert [(m.round, m.home, m.away) for m in matches] == [
        (1, "A", "D"),
        (1, "C", "B"),
        (2, "D", "B"),
        (2, "A", "C"),
        (3, "C", "D"),
        (3, "B", "A"),
    ]
    assert all(m.status == MatchStatus.SCHEDULED and m.starts_at is None for m in matches)


def test_odd_number_of_teams_gives_each_team_one_rest() -> None:
    matches = round_robin(teams(5))

    rounds = sorted({m.round for m in matches})
    assert rounds == [1, 2, 3, 4, 5]
    resting = [
        set(teams(5)) - {t for m in matches if m.round == r for t in (m.home, m.away)}
        for r in rounds
    ]
    assert all(len(rest) == 1 for rest in resting)
    assert Counter(t for rest in resting for t in rest) == dict.fromkeys(teams(5), 1)


def test_double_swaps_home_and_away_in_second_leg() -> None:
    single = round_robin(teams(4))
    double = round_robin(teams(4), double=True)

    assert double[: len(single)] == single
    assert [(m.round, m.home, m.away) for m in double[len(single) :]] == [
        (m.round + 3, m.away, m.home) for m in single
    ]


@pytest.mark.parametrize("bad", [[], ["A"], ["A", "B", "A"]])
def test_invalid_teams_are_rejected(bad: list[str]) -> None:
    with pytest.raises(ValueError):
        round_robin(bad)


def pair_counts(matches: list[Match]) -> Counter[frozenset[str]]:
    return Counter(frozenset((m.home, m.away)) for m in matches)


@given(st.integers(2, 20), st.booleans())
def test_every_pair_meets_once_per_leg(n: int, double: bool) -> None:
    matches = round_robin(teams(n), double=double)

    counts = pair_counts(matches)
    assert len(counts) == n * (n - 1) // 2
    assert set(counts.values()) == {2 if double else 1}
    if double:
        assert {(m.home, m.away) for m in matches} == {
            (a, b) for a in teams(n) for b in teams(n) if a != b
        }


@given(st.integers(2, 20), st.booleans())
def test_no_team_plays_twice_in_a_round(n: int, double: bool) -> None:
    matches = round_robin(teams(n), double=double)

    for r in {m.round for m in matches}:
        playing = [t for m in matches if m.round == r for t in (m.home, m.away)]
        assert len(playing) == len(set(playing))
    legs = 2 if double else 1
    assert max(m.round for m in matches) == legs * (n - 1 + n % 2)


@given(st.integers(2, 20))
def test_home_and_away_are_balanced(n: int) -> None:
    matches = round_robin(teams(n))

    for team in teams(n):
        venues = ["H" if m.home == team else "A" for m in matches if team in (m.home, m.away)]
        assert abs(venues.count("H") - venues.count("A")) <= 1
        assert "HHH" not in "".join(venues) and "AAA" not in "".join(venues)
