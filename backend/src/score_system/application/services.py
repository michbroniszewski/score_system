"""Use cases: what the API (and later other clients) can do, on top of the repository.

Domain rules raise ValueError subclasses; this layer adds NotFoundError and ConflictError.
"""

from collections.abc import Callable, Mapping
from datetime import date
from typing import Any
from uuid import UUID

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


def create_competition(repo: Repository, slug: str, name: str, preset: str) -> CompetitionRow:
    if preset not in preset_names():
        raise ValueError(f"unknown preset {preset!r}, available: {preset_names()}")
    if repo.competition_by_slug(slug) is not None:
        raise ConflictError(f"competition {slug!r} already exists")
    repo.add_competition(slug, name, preset)
    return competition(repo, slug)


def club(repo: Repository, club_id: UUID) -> ClubRow:
    row = repo.club(club_id)
    if row is None:
        raise NotFoundError(f"club {club_id} not found")
    return row


def create_club(repo: Repository, name: str) -> ClubRow:
    if repo.club_by_name(name) is not None:
        raise ConflictError(f"club {name!r} already exists")
    return club(repo, repo.add_club(name))


def team(repo: Repository, team_id: UUID) -> TeamRow:
    row = repo.team(team_id)
    if row is None:
        raise NotFoundError(f"team {team_id} not found")
    return row


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
    repo.session.flush()
    return row


def team_in_competition(repo: Repository, slug: str, team_id: UUID) -> CompetitionRow:
    comp = competition(repo, slug)
    if all(t.id != team_id for t in repo.competition_teams(comp.id)):
        raise NotFoundError("the team is not entered in this competition")
    return comp


def enter_team(repo: Repository, slug: str, team_id: UUID) -> None:
    comp = competition(repo, slug)
    team(repo, team_id)
    if any(t.id == team_id for t in repo.competition_teams(comp.id)):
        raise ConflictError("the team is already entered")
    if repo.matches(comp.id):
        raise ConflictError("fixtures already exist; teams cannot be added any more")
    repo.enter_team(comp.id, team_id)


def generate_fixtures(repo: Repository, slug: str, double: bool) -> list[Match]:
    comp = competition(repo, slug)
    if repo.matches(comp.id):
        raise ConflictError("fixtures already exist")
    team_ids = [str(t.id) for t in repo.competition_teams(comp.id)]
    for match in round_robin(team_ids, double=double):
        repo.save_match(comp.id, match)
    return repo.matches(comp.id)


def match(repo: Repository, match_id: UUID) -> tuple[CompetitionRow, Match]:
    found = repo.match(match_id)
    if found is None:
        raise NotFoundError(f"match {match_id} not found")
    competition_id, stored = found
    comp = repo.session.get_one(CompetitionRow, competition_id)
    return comp, stored


def change_match(repo: Repository, match_id: UUID, change: MatchChange) -> Match:
    """Apply a domain edit (reschedule, record_result, ...) to a stored match."""
    comp, stored = match(repo, match_id)
    return repo.save_match(comp.id, change(stored, load_preset(comp.preset)))


def standings(repo: Repository, slug: str) -> list[StandingRow]:
    comp = competition(repo, slug)
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
    repo.session.flush()
    return row


def join_roster(
    repo: Repository,
    slug: str,
    team_id: UUID,
    player_id: UUID,
    number: int | None,
    position: str | None,
    joined_on: date | None,
) -> RosterEntryRow:
    comp = team_in_competition(repo, slug, team_id)
    player(repo, player_id)
    entries = [e for e, _ in repo.roster_entries(comp.id) if e.player_id == player_id]
    if any(e.left_on is None for e in entries):
        raise ConflictError("the player is already in a roster of this competition; leave it first")
    if joined_on is not None and any(e.left_on and joined_on < e.left_on for e in entries):
        raise ValueError("joined_on must not be before the day the player left a previous roster")
    return repo.add_roster_entry(comp.id, team_id, player_id, number, position, joined_on)


def leave_roster(repo: Repository, entry_id: UUID, left_on: date) -> RosterEntryRow:
    """End a roster entry; it stays in the history."""
    entry = repo.roster_entry(entry_id)
    if entry is None:
        raise NotFoundError(f"roster entry {entry_id} not found")
    if entry.left_on is not None:
        raise ConflictError("the player has already left this roster")
    if entry.joined_on is not None and left_on < entry.joined_on:
        raise ValueError("left_on must not be before joined_on")
    entry.left_on = left_on
    repo.session.flush()
    return entry


def add_event(
    repo: Repository, match_id: UUID, team_id: UUID, player_id: UUID, stat: str, value: int
) -> MatchEventRow:
    comp, stored = match(repo, match_id)
    if stored.status != MatchStatus.PLAYED:
        raise ConflictError("statistics can only be recorded for a played match")
    if str(team_id) not in (stored.home, stored.away):
        raise ValueError("the team does not play in this match")
    if stat not in load_preset(comp.preset).stats:
        raise ValueError(f"unknown statistic {stat!r}")
    # The player must be in the roster on the match day (or now, for a match without a date).
    day = stored.starts_at.date() if stored.starts_at else None
    entries = [e for e, _ in repo.roster_entries(comp.id, team_id) if e.player_id == player_id]
    if not any(_in_roster_on(e, day) for e in entries):
        raise ValueError("the player is not in this team's roster for this match")
    return repo.add_event(match_id, team_id, player_id, stat, value)


def _in_roster_on(entry: RosterEntryRow, day: date | None) -> bool:
    if day is None:
        return entry.left_on is None
    joined = entry.joined_on is None or entry.joined_on <= day
    return joined and (entry.left_on is None or entry.left_on >= day)


def delete_event(repo: Repository, event_id: UUID) -> None:
    row = repo.event(event_id)
    if row is None:
        raise NotFoundError(f"event {event_id} not found")
    repo.delete_event(row)


def player_stats(repo: Repository, slug: str) -> dict[str, dict[str, int]]:
    """Statistic totals per player (id as string) in a competition.

    Counts played matches only (a result corrected to a walkover keeps its events, but they
    no longer count), and skips statistics no longer in the preset.
    """
    comp = competition(repo, slug)
    rules = load_preset(comp.preset)
    events = [
        StatEvent(str(e.player_id), e.stat, e.value)
        for e in repo.competition_events(comp.id, MatchStatus.PLAYED)
        if e.stat in rules.stats
    ]
    return player_totals(events, rules)
