"""Editing fixtures. Every function returns a new Match; the input is never modified."""

from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime

from score_system.domain.models import Match, MatchResult, MatchStatus, SetScore
from score_system.domain.results import validate_sets
from score_system.domain.rules import RuleSet

S = MatchStatus
OPEN = {S.SCHEDULED, S.POSTPONED}
# A recorded result or walkover can be corrected.
RESULT_ALLOWED = {S.SCHEDULED, S.POSTPONED, S.PLAYED, S.WALKOVER}


class InvalidTransitionError(ValueError):
    pass


def reschedule(match: Match, starts_at: datetime, venue: str | None = None) -> Match:
    """Set a (new) date, and optionally a venue; the current venue is kept when None."""
    _require(match, OPEN, "reschedule")
    if starts_at.tzinfo is None:
        raise ValueError("starts_at must be timezone-aware")
    return replace(
        match,
        status=S.SCHEDULED,
        starts_at=starts_at.astimezone(UTC),
        venue=match.venue if venue is None else venue,
    )


def postpone(match: Match) -> Match:
    """Postpone until a new date is agreed (see `reschedule`)."""
    _require(match, {S.SCHEDULED}, "postpone")
    return replace(match, status=S.POSTPONED, starts_at=None)


def cancel(match: Match) -> Match:
    _require(match, OPEN, "cancel")
    return replace(match, status=S.CANCELLED)


def record_result(match: Match, sets: Iterable[SetScore], ruleset: RuleSet) -> Match:
    _require(match, RESULT_ALLOWED, "record a result for")
    sets = tuple(sets)
    validate_sets(sets, ruleset)
    return replace(match, status=S.PLAYED, sets=sets, walkover_winner=None)


def record_walkover(match: Match, winner: str) -> Match:
    _require(match, RESULT_ALLOWED, "record a walkover for")
    if winner not in (match.home, match.away):
        raise ValueError(f"{winner!r} does not play in this match")
    return replace(match, status=S.WALKOVER, sets=(), walkover_winner=winner)


def standings_results(matches: Iterable[Match], ruleset: RuleSet) -> list[MatchResult]:
    """Results that count in the standings: played matches and walkovers."""
    results = []
    for match in matches:
        if match.status == S.PLAYED:
            results.append(MatchResult(match.home, match.away, match.sets))
        elif match.status == S.WALKOVER:
            won, lost = ruleset.walkover_set
            score = (
                SetScore(won, lost) if match.walkover_winner == match.home else SetScore(lost, won)
            )
            results.append(MatchResult(match.home, match.away, (score,) * ruleset.sets_to_win))
    return results


def _require(match: Match, allowed: set[MatchStatus], action: str) -> None:
    if match.status not in allowed:
        raise InvalidTransitionError(f"cannot {action} a {match.status} match")
