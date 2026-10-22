"""Request and response bodies of API v1: the contract shared with every client."""

from datetime import date
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from score_system.domain.models import MatchStatus
from score_system.infrastructure.orm import DEFAULT_TIMEZONE

Name = Field(min_length=1, max_length=200)


class Input(BaseModel):
    """Base of request bodies: leading and trailing spaces are dropped from strings."""

    model_config = ConfigDict(str_strip_whitespace=True)


class ClubIn(Input):
    name: str = Name


class TeamRef(BaseModel):
    id: UUID
    name: str


class ClubOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class ClubDetail(ClubOut):
    teams: list[TeamRef]


class TeamIn(Input):
    name: str = Name
    short_name: str | None = Field(default=None, max_length=20)
    club_id: UUID | None = None
    saved: bool = Field(default=False, description="Keep the team in the general base.")


class TeamPatch(Input):
    """Only the fields sent are changed; null clears short_name or club_id."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    short_name: str | None = Field(default=None, max_length=20)
    club_id: UUID | None = None
    saved: bool | None = None

    @model_validator(mode="after")
    def _required_fields_not_null(self) -> Self:
        _reject_null(self, "name", "saved")
        return self


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    short_name: str | None
    club_id: UUID | None
    saved: bool


class PresetOut(BaseModel):
    """What a client needs from a preset to enter data: set count and statistic codes."""

    name: str
    discipline: str
    sets_to_win: int
    stats: list[str] = Field(description="Statistic codes for match events, e.g. aces.")


class CompetitionIn(Input):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=100)
    name: str = Name
    preset: str
    timezone: str = Field(
        default=DEFAULT_TIMEZONE,
        max_length=64,
        description="IANA time zone; a match's day (for rosters) is its date in this zone.",
    )
    playoff: str | None = Field(
        default=None, description="Play-off format (GET /playoffs), fixed for the season."
    )

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"unknown time zone {value!r}") from None
        return value


class CompetitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    preset: str
    timezone: str
    playoff: str | None


class EntryIn(Input):
    """Enter an existing team (`team_id`) or create a new one (`team`)."""

    team_id: UUID | None = None
    team: TeamIn | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.team_id is None) == (self.team is None):
            raise ValueError("give exactly one of team_id and team")
        return self


class FixturesIn(Input):
    double: bool = Field(default=False, description="Second leg with home and away swapped.")


class SetIn(Input):
    home: int = Field(ge=0)
    away: int = Field(ge=0)


class SetOut(BaseModel):
    home: int
    away: int


class MatchOut(BaseModel):
    id: UUID
    round: int
    home: TeamRef
    away: TeamRef
    status: MatchStatus
    starts_at: AwareDatetime | None
    venue: str | None
    sets: list[SetOut]
    walkover_winner: UUID | None
    series: str | None = Field(description="Play-off series; `round` is then the game number.")


class SeriesFormatOut(BaseModel):
    key: str
    sides: list[str] = Field(description="Team sources: seed N, winner X, loser X.")
    wins: int


class PlayoffFormatOut(BaseModel):
    id: str
    name: str
    seeds: int
    series: list[SeriesFormatOut]


class SeriesOut(BaseModel):
    key: str
    wins: int = Field(description="Games needed to win the series.")
    home: TeamRef | None = Field(description="The better-seeded team, host of game 1.")
    away: TeamRef | None
    home_wins: int
    away_wins: int
    winner: TeamRef | None
    matches: list[MatchOut]


class PlaceOut(BaseModel):
    place: int
    team: TeamRef | None = Field(description="None until the series deciding it ends.")


class PlayoffOut(BaseModel):
    format: str
    started: bool
    series: list[SeriesOut]
    places: list[PlaceOut] = Field(description="Final classification; empty until started.")


class RescheduleIn(Input):
    starts_at: AwareDatetime
    venue: str | None = Field(
        default=None, max_length=200, description="Omitted: keep the venue; null: clear it."
    )


class ResultIn(Input):
    sets: list[SetIn] = Field(min_length=1)


class WalkoverIn(Input):
    winner: UUID


class StandingOut(BaseModel):
    position: int
    team: TeamRef
    played: int
    wins: int
    losses: int
    points: int
    sets_won: int
    sets_lost: int
    small_points_won: int
    small_points_lost: int


class PlayerIn(Input):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class PlayerPatch(Input):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def _required_fields_not_null(self) -> Self:
        _reject_null(self, "first_name", "last_name")
        return self


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str


class PlayerRef(BaseModel):
    id: UUID
    name: str


class RosterIn(Input):
    """Add an existing player (`player_id`) or a new one (`player`) to a team's roster."""

    player_id: UUID | None = None
    player: PlayerIn | None = None
    number: int | None = Field(default=None, ge=0, le=999)
    position: str | None = Field(default=None, max_length=50)
    joined_on: date | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.player_id is None) == (self.player is None):
            raise ValueError("give exactly one of player_id and player")
        return self


class RosterEntryOut(BaseModel):
    id: UUID
    team_id: UUID
    player: PlayerOut
    number: int | None
    position: str | None
    joined_on: date | None
    left_on: date | None = Field(description="Empty while the player is in the roster.")


class LeaveIn(Input):
    left_on: date


class EventIn(Input):
    team_id: UUID
    player_id: UUID
    stat: str = Field(description="A statistic of the competition's preset, e.g. aces.")
    value: int = Field(default=1, ge=1, le=1000)


class EventOut(BaseModel):
    id: UUID
    team_id: UUID
    player: PlayerRef
    stat: str
    value: int


class PlayerStatsOut(BaseModel):
    player: PlayerRef
    team: TeamRef | None = Field(description="The player's current team, if any.")
    stats: dict[str, int]


def _reject_null(model: BaseModel, *fields: str) -> None:
    """In a PATCH body a field may be left out, but these may not be sent as null."""
    nulls = [f for f in fields if f in model.model_fields_set and getattr(model, f) is None]
    if nulls:
        raise ValueError(f"{', '.join(nulls)} cannot be null")
