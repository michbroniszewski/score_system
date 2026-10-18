from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


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


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    POSTPONED = "postponed"  # waiting for a new date
    PLAYED = "played"
    WALKOVER = "walkover"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Match:
    """A fixture: who plays whom in which round, and what happened to it."""

    round: int
    home: str
    away: str
    status: MatchStatus = MatchStatus.SCHEDULED
    starts_at: datetime | None = None  # timezone-aware, stored in UTC
    venue: str | None = None
    sets: tuple[SetScore, ...] = ()  # only when PLAYED
    walkover_winner: str | None = None  # only when WALKOVER
    id: UUID | None = None  # assigned when the match is first stored


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
