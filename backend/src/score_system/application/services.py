"""Use cases: what the API (and later other clients) can do, on top of the repository.

Rejected requests raise DomainError (as the domain rules do), NotFoundError or ConflictError.
Functions about one competition take its row: look it up once with `competition`.
"""

from collections.abc import Callable, Mapping
from datetime import date, datetime
from typing import Any, NamedTuple
from uuid import UUID
from zoneinfo import ZoneInfo

from score_system.domain.errors import DomainError
from score_system.domain.fixtures import round_robin
from score_system.domain.matches import standings_results
from score_system.domain.models import Match, MatchStatus, StandingRow, StatEvent
from score_system.domain.rules import RuleSet
from score_system.domain.standings import compute_standings
from score_system.domain.stats import player_totals
from score_system.infrastructure.orm import (
    ClubRow,
    CompetitionRow,
    MatchEventRow,
    PlayerRow,
    RosterEntryRow,
    TeamRow,
)
from score_system.infrastructure.presets import load_preset, preset_names
from score_system.infrastructure.repository import Repository

MatchChange = Callable[[Match, RuleSet], Match]


class NotFoundError(LookupError):
    pass


class ConflictError(Exception):
    pass


def competition(repo: Repository, slug: str) -> CompetitionRow:
    row = repo.competition_by_slug(slug)
    if row is None:
        raise NotFoundError(f"competition {slug!r} not found")
    return row


def preset(name: str) -> RuleSet:
    if name not in preset_names():
        raise NotFoundError(f"preset {name!r} not found")
    return load_preset(name)


def competitions(repo: Repository) -> list[CompetitionRow]:
    return repo.competitions()


def competition_teams(repo: Repository, comp: CompetitionRow) -> list[TeamRow]:
    return repo.competition_teams(comp.id)


def team_names(repo: Repository, comp: CompetitionRow) -> dict[str, str]:
    """Names of the competition's teams by team id (as in domain objects)."""
    return {str(t.id): t.name for t in repo.competition_teams(comp.id)}


def create_competition(
    repo: Repository, slug: str, name: str, preset: str, timezone: str
) -> CompetitionRow:
    if preset not in preset_names():
        raise DomainError(f"unknown preset {preset!r}, available: {list(preset_names())}")
    if repo.competition_by_slug(slug) is not None:
        raise ConflictError(f"competition {slug!r} already exists")
    repo.add_competition(slug, name, preset, timezone)
    return competition(repo, slug)


def club(repo: Repository, club_id: UUID) -> ClubRow:
    row = repo.club(club_id)
    if row is None:
        raise NotFoundError(f"club {club_id} not found")
    return row


def clubs(repo: Repository) -> list[ClubRow]:
    return repo.clubs()


def club_teams(repo: Repository, club_id: UUID) -> tuple[ClubRow, list[TeamRow]]:
    return club(repo, club_id), repo.club_teams(club_id)


def create_club(repo: Repository, name: str) -> ClubRow:
    if repo.club_by_name(name) is not None:
        raise ConflictError(f"club {name!r} already exists")
    return club(repo, repo.add_club(name))


def team(repo: Repository, team_id: UUID) -> TeamRow:
    row = repo.team(team_id)
    if row is None:
        raise NotFoundError(f"team {team_id} not found")
    return row


def saved_teams(repo: Repository) -> list[TeamRow]:
    return repo.saved_teams()


def create_team(
    repo: Repository, name: str, short_name: str | None, club_id: UUID | None, saved: bool
) -> TeamRow:
    if club_id is not None:
        club(repo, club_id)
    if repo.team_by_name(name) is not None:
        raise ConflictError(f"team {name!r} already exists")
    return team(repo, repo.add_team(name, short_name, club_id, saved))


def update_team(repo: Repository, team_id: UUID, changes: Mapping[str, Any]) -> TeamRow:
    """Change the fields present in `changes`; short_name and club_id can be set to None."""
    row = team(repo, team_id)
    if "name" in changes and changes["name"] != row.name:
        if repo.team_by_name(changes["name"]) is not None:
            raise ConflictError(f"team {changes['name']!r} already exists")
        row.name = changes["name"]
    if "short_name" in changes:
        row.short_name = changes["short_name"]
    if "club_id" in changes:
        row.club_id = None if changes["club_id"] is None else club(repo, changes["club_id"]).id
    if "saved" in changes:
        row.saved = changes["saved"]
    repo.flush()
    return row


def team_in_competition(repo: Repository, comp: CompetitionRow, team_id: UUID) -> None:
    if not repo.is_entered(comp.id, team_id):
        raise NotFoundError("the team is not entered in this competition")


def enter_team(repo: Repository, comp: CompetitionRow, team_id: UUID) -> None:
    repo.lock_competition(comp.id)
    team(repo, team_id)
    if repo.is_entered(comp.id, team_id):
        raise ConflictError("the team is already entered")
    if repo.has_matches(comp.id):
        raise ConflictError("fixtures already exist; teams cannot be added any more")
    repo.enter_team(comp.id, team_id)


def generate_fixtures(repo: Repository, comp: CompetitionRow, double: bool) -> list[Match]:
    repo.lock_competition(comp.id)
    if repo.has_matches(comp.id):
        raise ConflictError("fixtures already exist")
    team_ids = [str(t.id) for t in repo.competition_teams(comp.id)]
    repo.add_matches(comp.id, round_robin(team_ids, double=double))
    return repo.matches(comp.id)


def matches(repo: Repository, comp: CompetitionRow) -> list[Match]:
    return repo.matches(comp.id)


def match(repo: Repository, match_id: UUID) -> tuple[CompetitionRow, Match]:
    found = repo.match(match_id)
    if found is None:
        raise NotFoundError(f"match {match_id} not found")
    return found


def change_match(
    repo: Repository, match_id: UUID, change: MatchChange
) -> tuple[CompetitionRow, Match]:
    """Apply a domain edit (reschedule, record_result, ...) to a stored match."""
    comp, stored = match(repo, match_id)
    return comp, repo.save_match(comp.id, change(stored, load_preset(comp.preset)))


def standings(repo: Repository, comp: CompetitionRow) -> list[StandingRow]:
    rules = load_preset(comp.preset)
    teams = [str(t.id) for t in repo.competition_teams(comp.id)]
    return compute_standings(teams, standings_results(repo.matches(comp.id), rules), rules)


def player(repo: Repository, player_id: UUID) -> PlayerRow:
    row = repo.player(player_id)
    if row is None:
        raise NotFoundError(f"player {player_id} not found")
    return row


def create_player(repo: Repository, first_name: str, last_name: str) -> PlayerRow:
    return player(repo, repo.add_player(first_name, last_name))


def update_player(
    repo: Repository, player_id: UUID, first_name: str | None, last_name: str | None
) -> PlayerRow:
    row = player(repo, player_id)
    if first_name is not None:
        row.first_name = first_name
    if last_name is not None:
        row.last_name = last_name
    repo.flush()
    return row


def competition_roster(
    repo: Repository, comp: CompetitionRow
) -> list[tuple[RosterEntryRow, PlayerRow]]:
    return repo.roster_entries(comp.id)


def roster(
    repo: Repository, comp: CompetitionRow, team_id: UUID
) -> list[tuple[RosterEntryRow, PlayerRow]]:
    team_in_competition(repo, comp, team_id)
    return repo.roster_entries(comp.id, team_id)


def join_roster(
    repo: Repository,
    comp: CompetitionRow,
    team_id: UUID,
    player_id: UUID,
    number: int | None,
    position: str | None,
    joined_on: date | None,
) -> RosterEntryRow:
    team_in_competition(repo, comp, team_id)
    player(repo, player_id)
    entries = repo.player_entries(comp.id, player_id)
    if any(e.left_on is None for e in entries):
        raise ConflictError("the player is already in a roster of this competition; leave it first")
    if entries and joined_on is None:
        raise DomainError("joined_on is required when the player was in a roster before")
    if joined_on is not None and any(e.left_on and joined_on < e.left_on for e in entries):
        raise DomainError("joined_on must not be before the day the player left a previous roster")
    return repo.add_roster_entry(comp.id, team_id, player_id, number, position, joined_on)


def leave_roster(repo: Repository, entry_id: UUID, left_on: date) -> RosterEntryRow:
    """End a roster entry; it stays in the history."""
    entry = repo.roster_entry(entry_id)
    if entry is None:
        raise NotFoundError(f"roster entry {entry_id} not found")
    if entry.left_on is not None:
        raise ConflictError("the player has already left this roster")
    if entry.joined_on is not None and left_on < entry.joined_on:
        raise DomainError("left_on must not be before joined_on")
    comp = repo.competition(entry.competition_id)
    starts = repo.event_match_starts(entry.competition_id, entry.team_id, entry.player_id)
    if any(_day(start, comp) > left_on for start in starts if start is not None):
        raise DomainError("the player has statistics for this team in matches after left_on")
    entry.left_on = left_on
    repo.flush()
    return entry


def add_event(
    repo: Repository, match_id: UUID, team_id: UUID, player_id: UUID, stat: str, value: int
) -> MatchEventRow:
    comp, stored = match(repo, match_id)
    if stored.status != MatchStatus.PLAYED:
        raise ConflictError("statistics can only be recorded for a played match")
    if str(team_id) not in (stored.home, stored.away):
        raise DomainError("the team does not play in this match")
    if stat not in load_preset(comp.preset).stats:
        raise DomainError(f"unknown statistic {stat!r}")
    # The player must be in the roster on the match day (or now, for a match without a date).
    day = _day(stored.starts_at, comp) if stored.starts_at else None
    entries = repo.player_entries(comp.id, player_id, team_id)
    if not any(_in_roster_on(e, day) for e in entries):
        raise DomainError("the player is not in this team's roster for this match")
    return repo.add_event(match_id, team_id, player_id, stat, value)


def _day(moment: datetime, comp: CompetitionRow) -> date:
    """The date of `moment` in the competition's time zone."""
    return moment.astimezone(ZoneInfo(comp.timezone)).date()


def _in_roster_on(entry: RosterEntryRow, day: date | None) -> bool:
    if day is None:
        return entry.left_on is None
    joined = entry.joined_on is None or entry.joined_on <= day
    return joined and (entry.left_on is None or entry.left_on >= day)


def match_events(repo: Repository, match_id: UUID) -> list[tuple[MatchEventRow, PlayerRow]]:
    match(repo, match_id)
    return repo.events(match_id)


def delete_event(repo: Repository, event_id: UUID) -> None:
    row = repo.event(event_id)
    if row is None:
        raise NotFoundError(f"event {event_id} not found")
    repo.delete_event(row)


class PlayerStats(NamedTuple):
    player: PlayerRow
    team_id: UUID | None  # the player's current team, if any
    stats: dict[str, int]


def player_stats(repo: Repository, comp: CompetitionRow) -> list[PlayerStats]:
    """Statistic totals of the competition's players who have any, by last name.

    Counts played matches only (a result corrected to a walkover keeps its events, but they
    no longer count), and skips statistics no longer in the preset.
    """
    rules = load_preset(comp.preset)
    events = [
        StatEvent(str(e.player_id), e.stat, e.value)
        for e in repo.competition_events(comp.id, MatchStatus.PLAYED)
        if e.stat in rules.stats
    ]
    totals = player_totals(events, rules)
    players: dict[UUID, PlayerRow] = {}  # in roster order, i.e. by last name
    current_team: dict[UUID, UUID] = {}
    for entry, row in repo.roster_entries(comp.id):
        players[row.id] = row
        if entry.left_on is None:
            current_team[row.id] = entry.team_id
    return [
        PlayerStats(row, current_team.get(pid), totals[str(pid)])
        for pid, row in players.items()
        if str(pid) in totals
    ]
