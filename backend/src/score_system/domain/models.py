from dataclasses import dataclass


@dataclass(frozen=True)
class SetScore:
    home: int
    away: int


@dataclass(frozen=True)
class MatchResult:
    """A played match: team identifiers and the score of every set, in order."""

    home: str
    away: str
    sets: tuple[SetScore, ...]


@dataclass(frozen=True)
class StandingRow:
    position: int
    team: str
    played: int
    wins: int
    losses: int
    points: int
    sets_won: int
    sets_lost: int
    small_points_won: int
    small_points_lost: int
