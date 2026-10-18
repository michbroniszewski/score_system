"""Standings criteria. Each one maps a row to a value where higher ranks better.

A ruleset lists criteria by name; a new criterion is one new entry here.
"""

from collections.abc import Callable
from fractions import Fraction
from typing import Any

from score_system.domain.models import StandingRow


def _ratio(won: int, lost: int) -> Fraction | float:
    # Nothing lost ranks above any finite ratio; nothing played at all ranks as zero.
    if lost == 0:
        return float("inf") if won > 0 else 0
    return Fraction(won, lost)


TIEBREAKERS: dict[str, Callable[[StandingRow], Any]] = {
    "points": lambda row: row.points,
    "wins": lambda row: row.wins,
    "set_ratio": lambda row: _ratio(row.sets_won, row.sets_lost),
    "small_points_ratio": lambda row: _ratio(row.small_points_won, row.small_points_lost),
}
