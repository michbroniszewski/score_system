from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Time zone of competitions created without one; match days are counted in it.
DEFAULT_TIMEZONE = "Europe/Warsaw"


class Base(DeclarativeBase):
    pass


competition_teams = Table(
    "competition_teams",
    Base.metadata,
    Column("competition_id", ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True),
    Column("team_id", ForeignKey("teams.id", ondelete="RESTRICT"), primary_key=True),
)


class CompetitionRow(Base):
    __tablename__ = "competitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    # Name of the rules preset file in backend/presets/, e.g. "volleyball".
    preset: Mapped[str] = mapped_column(String(50))
    # IANA time zone name, e.g. "Europe/Warsaw". Dates are stored in UTC; a match's day
    # (for the roster on match day) is its date in this zone.
    timezone: Mapped[str] = mapped_column(
        String(64), default=DEFAULT_TIMEZONE, server_default=DEFAULT_TIMEZONE
    )


class ClubRow(Base):
    """A club can field several teams, in the same or in different competitions."""

    __tablename__ = "clubs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)


class TeamRow(Base):
    __tablename__ = "teams"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    short_name: Mapped[str | None] = mapped_column(String(20))
    club_id: Mapped[UUID | None] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"))
    # Saved teams form the general base offered when building new competitions;
    # the others exist only in the competitions they were entered in.
    saved: Mapped[bool] = mapped_column(default=False, server_default=false())


class MatchRow(Base):
    __tablename__ = "matches"
    __table_args__ = (CheckConstraint("home_team_id <> away_team_id", name="different_teams"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    competition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), index=True
    )
    round: Mapped[int]
    home_team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"))
    status: Mapped[str] = mapped_column(String(20))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    venue: Mapped[str | None] = mapped_column(String(200))
    # Set scores as [[home, away], ...]; empty unless the match was played.
    sets: Mapped[list[list[int]]] = mapped_column(JSONB, default=list)
    walkover_winner_id: Mapped[UUID | None] = mapped_column(ForeignKey("teams.id"))


class PlayerRow(Base):
    __tablename__ = "players"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))


class RosterEntryRow(Base):
    """A player in a team's roster for one competition, from `joined_on` to `left_on`.

    Leaving ends the entry instead of deleting it, so the roster history is kept.
    Number and position live here because they can differ between teams.
    """

    __tablename__ = "roster_entries"
    __table_args__ = (
        # A player is in at most one active roster per competition.
        Index(
            "one_active_entry_per_competition",
            "competition_id",
            "player_id",
            unique=True,
            postgresql_where="left_on IS NULL",
        ),
        CheckConstraint("left_on IS NULL OR joined_on IS NULL OR left_on >= joined_on"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    competition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"))
    player_id: Mapped[UUID] = mapped_column(ForeignKey("players.id"))
    number: Mapped[int | None]
    position: Mapped[str | None] = mapped_column(String(50))
    joined_on: Mapped[date | None]
    left_on: Mapped[date | None]


class MatchEventRow(Base):
    """A player's statistic in a match, e.g. 3 aces (stat codes come from the preset)."""

    __tablename__ = "match_events"
    __table_args__ = (CheckConstraint("value > 0"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"))
    player_id: Mapped[UUID] = mapped_column(ForeignKey("players.id"))
    stat: Mapped[str] = mapped_column(String(50))
    value: Mapped[int]
