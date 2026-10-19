from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from score_system.domain.models import MatchResult, StandingRow
from score_system.domain.results import InvalidResultError, validate_sets
from score_system.domain.rules import RuleSet
from score_system.domain.tiebreakers import TIEBREAKERS


@dataclass
class _Tally:
    played: int = 0
    wins: int = 0
    losses: int = 0
    points: int = 0
    sets_won: int = 0
    sets_lost: int = 0
    small_points_won: int = 0
    small_points_lost: int = 0


def compute_standings(
    teams: Sequence[str], matches: Iterable[MatchResult], ruleset: RuleSet
) -> list[StandingRow]:
    """Rank teams by the ruleset's tiebreakers, in order.

    Teams still tied after every tiebreaker keep their order from `teams`.
    """
    tallies = {team: _Tally() for team in teams}
    for match in matches:
        _add_match(tallies, match, ruleset)

    rows = [StandingRow(position=0, team=team, **vars(t)) for team, t in tallies.items()]
    keys = [TIEBREAKERS[name] for name in ruleset.tiebreakers]
    rows.sort(key=lambda row: tuple(key(row) for key in keys), reverse=True)
    # sort(reverse=True) is still stable, so tied teams keep their order from `teams`.
    return [replace(row, position=i) for i, row in enumerate(rows, start=1)]


def _add_match(tallies: dict[str, _Tally], match: MatchResult, ruleset: RuleSet) -> None:
    for team in (match.home, match.away):
        if team not in tallies:
            raise InvalidResultError(f"unknown team {team!r}")
    if match.home == match.away:
        raise InvalidResultError(f"team {match.home!r} cannot play itself")
    home_sets, away_sets = validate_sets(match.sets, ruleset)
    home_won = home_sets > away_sets
    winner_sets, loser_sets = (home_sets, away_sets) if home_won else (away_sets, home_sets)
    winner_points, loser_points = ruleset.points[f"{winner_sets}:{loser_sets}"]

    home_small = sum(s.home for s in match.sets)
    away_small = sum(s.away for s in match.sets)
    _record(
        tallies[match.home],
        home_won,
        winner_points if home_won else loser_points,
        home_sets,
        away_sets,
        home_small,
        away_small,
    )
    _record(
        tallies[match.away],
        not home_won,
        loser_points if home_won else winner_points,
        away_sets,
        home_sets,
        away_small,
        home_small,
    )


def _record(
    tally: _Tally,
    won: bool,
    points: int,
    sets_won: int,
    sets_lost: int,
    small_won: int,
    small_lost: int,
) -> None:
    tally.played += 1
    tally.wins += won
    tally.losses += not won
    tally.points += points
    tally.sets_won += sets_won
    tally.sets_lost += sets_lost
    tally.small_points_won += small_won
    tally.small_points_lost += small_lost
