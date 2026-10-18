from collections.abc import Iterable

from score_system.domain.models import StatEvent
from score_system.domain.rules import RuleSet


def player_totals(events: Iterable[StatEvent], ruleset: RuleSet) -> dict[str, dict[str, int]]:
    """Sum of every ruleset statistic per player (zero when a player has none of it)."""
    totals: dict[str, dict[str, int]] = {}
    for event in events:
        if event.stat not in ruleset.stats:
            raise ValueError(f"unknown statistic {event.stat!r}, expected one of {ruleset.stats}")
        row = totals.setdefault(event.player, dict.fromkeys(ruleset.stats, 0))
        row[event.stat] += event.value
    return totals
