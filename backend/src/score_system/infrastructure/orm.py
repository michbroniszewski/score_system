from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
