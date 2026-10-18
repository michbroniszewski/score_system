from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone

import pytest

from score_system.domain.matches import (
    InvalidTransitionError,
    cancel,
    postpone,
    record_result,
    record_walkover,
    reschedule,
    standings_results,
)
from score_system.domain.models import Match, MatchResult, MatchStatus, SetScore
from score_system.domain.results import InvalidResultError
from score_system.domain.rules import RuleSet
from score_system.domain.standings import compute_standings

S = MatchStatus
CET = timezone(timedelta(hours=1))
FRIDAY_8PM = datetime(2026, 11, 6, 20, 0, tzinfo=CET)
STRAIGHT_WIN = [SetScore(25, 20)] * 3


@pytest.fixture
def match() -> Match:
    return Match(round=1, home="A", away="B")


def test_reschedule_stores_utc_and_keeps_venue(match: Match) -> None:
    with_venue = reschedule(match, FRIDAY_8PM, venue="Hall 1")
    moved = reschedule(with_venue, FRIDAY_8PM + timedelta(days=1))

    assert moved.starts_at == datetime(2026, 11, 7, 19, 0, tzinfo=UTC)
    assert moved.starts_at is not None and moved.starts_at.tzinfo == UTC
    assert moved.venue == "Hall 1"
    assert moved.status == S.SCHEDULED


def test_reschedule_rejects_naive_datetime(match: Match) -> None:
    with pytest.raises(ValueError):
        reschedule(match, datetime(2026, 11, 6, 20, 0))


def test_postpone_then_reschedule(match: Match) -> None:
    postponed = postpone(reschedule(match, FRIDAY_8PM))

    assert (postponed.status, postponed.starts_at) == (S.POSTPONED, None)
    assert reschedule(postponed, FRIDAY_8PM).status == S.SCHEDULED


def test_record_result(match: Match, volleyball: RuleSet) -> None:
    played = record_result(match, STRAIGHT_WIN, volleyball)

    assert played.status == S.PLAYED
    assert played.sets == tuple(STRAIGHT_WIN)
    assert match.status == S.SCHEDULED  # the input is not modified


def test_record_result_rejects_invalid_sets(match: Match, volleyball: RuleSet) -> None:
    with pytest.raises(InvalidResultError):
        record_result(match, [SetScore(25, 20)] * 2, volleyball)


def test_walkover_and_correction(match: Match, volleyball: RuleSet) -> None:
    walkover = record_walkover(match, "B")
    corrected = record_result(walkover, STRAIGHT_WIN, volleyball)

    assert (walkover.status, walkover.walkover_winner) == (S.WALKOVER, "B")
    assert (corrected.status, corrected.walkover_winner) == (S.PLAYED, None)
    assert record_walkover(corrected, "A").sets == ()


def test_walkover_winner_must_play_in_match(match: Match) -> None:
    with pytest.raises(ValueError):
        record_walkover(match, "C")


@pytest.mark.parametrize(
    ("status", "action"),
    [
        (S.PLAYED, lambda m: reschedule(m, FRIDAY_8PM)),
        (S.CANCELLED, lambda m: reschedule(m, FRIDAY_8PM)),
        (S.POSTPONED, postpone),
        (S.PLAYED, postpone),
        (S.PLAYED, cancel),
        (S.WALKOVER, cancel),
        (S.CANCELLED, lambda m: record_walkover(m, "A")),
    ],
)
def test_invalid_transitions(status: MatchStatus, action: Callable[[Match], Match]) -> None:
    with pytest.raises(InvalidTransitionError):
        action(Match(round=1, home="A", away="B", status=status))


def test_standings_results_counts_played_and_walkovers(volleyball: RuleSet) -> None:
    fixtures = [
        record_result(Match(1, "A", "B"), STRAIGHT_WIN, volleyball),
        record_walkover(Match(1, "C", "D"), "D"),
        cancel(Match(2, "A", "C")),
        postpone(Match(2, "B", "D")),
        Match(3, "A", "D"),
    ]

    results = standings_results(fixtures, volleyball)

    assert results == [
        MatchResult("A", "B", tuple(STRAIGHT_WIN)),
        MatchResult("C", "D", (SetScore(0, 25),) * 3),
    ]
    rows = {r.team: r for r in compute_standings(["A", "B", "C", "D"], results, volleyball)}
    assert (rows["D"].points, rows["D"].small_points_won, rows["C"].small_points_lost) == (
        3,
        75,
        75,
    )
