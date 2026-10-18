from collections.abc import Sequence

from score_system.domain.models import SetScore
from score_system.domain.rules import RuleSet


class InvalidResultError(ValueError):
    pass


def validate_sets(sets: Sequence[SetScore], ruleset: RuleSet) -> None:
    """Raise InvalidResultError unless `sets` is a complete match under `ruleset`."""
    if not sets or any(s.home == s.away or s.home < 0 or s.away < 0 for s in sets):
        raise InvalidResultError(f"every set needs a winner and non-negative scores: {sets}")

    home_sets = sum(1 for s in sets if s.home > s.away)
    away_sets = len(sets) - home_sets
    home_won = home_sets > away_sets
    winner_sets, loser_sets = (home_sets, away_sets) if home_won else (away_sets, home_sets)
    last_set_won_by_winner = (sets[-1].home > sets[-1].away) == home_won
    if not (
        winner_sets == ruleset.sets_to_win and loser_sets < winner_sets and last_set_won_by_winner
    ):
        raise InvalidResultError(
            f"a match ends as soon as a team wins {ruleset.sets_to_win} sets: {sets}"
        )
