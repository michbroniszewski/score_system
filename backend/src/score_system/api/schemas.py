"""Request and response bodies of API v1: the contract shared with every client."""

from datetime import date
from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from score_system.domain.models import MatchStatus

Name = Field(min_length=1, max_length=200)


class ClubIn(BaseModel):
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


class TeamIn(BaseModel):
    name: str = Name
    short_name: str | None = Field(default=None, max_length=20)
    club_id: UUID | None = None
    saved: bool = Field(default=False, description="Keep the team in the general base.")


class TeamPatch(BaseModel):
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


class CompetitionIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=100)
    name: str = Name
    preset: str


class CompetitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    preset: str


class EntryIn(BaseModel):
    """Enter an existing team (`team_id`) or create a new one (`team`)."""

    team_id: UUID | None = None
    team: TeamIn | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.team_id is None) == (self.team is None):
            raise ValueError("give exactly one of team_id and team")
        return self


class FixturesIn(BaseModel):
    double: bool = Field(default=False, description="Second leg with home and away swapped.")


class SetIn(BaseModel):
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


class RescheduleIn(BaseModel):
    starts_at: AwareDatetime
    venue: str | None = Field(default=None, max_length=200)


class ResultIn(BaseModel):
    sets: list[SetIn] = Field(min_length=1)


class WalkoverIn(BaseModel):
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


class PlayerIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class PlayerPatch(BaseModel):
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


class RosterIn(BaseModel):
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


class LeaveIn(BaseModel):
    left_on: date


class EventIn(BaseModel):
    team_id: UUID
    player_id: UUID
    stat: str = Field(description="A statistic of the competition's preset, e.g. aces.")
    value: int = Field(default=1, ge=1)


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
