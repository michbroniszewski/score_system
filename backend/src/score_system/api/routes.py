from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from score_system.api.deps import get_repo
from score_system.api.schemas import (
    ClubDetail,
    ClubIn,
    ClubOut,
    CompetitionIn,
    CompetitionOut,
    EntryIn,
    EventIn,
    EventOut,
    FixturesIn,
    LeaveIn,
    MatchOut,
    PlayerIn,
    PlayerOut,
    PlayerPatch,
    PlayerRef,
    PlayerStatsOut,
    RescheduleIn,
    ResultIn,
    RosterEntryOut,
    RosterIn,
    SetOut,
    StandingOut,
    TeamIn,
    TeamOut,
    TeamPatch,
    TeamRef,
    WalkoverIn,
)
from score_system.application import services
from score_system.domain import matches as edits
from score_system.domain.models import Match, SetScore, StandingRow
from score_system.infrastructure.orm import MatchEventRow, PlayerRow, RosterEntryRow
from score_system.infrastructure.presets import preset_names
from score_system.infrastructure.repository import Repository

router = APIRouter(prefix="/api/v1")
# scope="function": the transaction ends (commits) before the response is sent, so a client
# never gets a success for data that is not stored yet, or not stored at all.
Repo = Annotated[Repository, Depends(get_repo, scope="function")]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/presets")
def list_presets() -> list[str]:
    """Discipline rule presets a competition can use."""
    return preset_names()


# --- clubs --------------------------------------------------------------------


@router.get("/clubs")
def list_clubs(repo: Repo) -> list[ClubOut]:
    return [ClubOut.model_validate(c) for c in repo.clubs()]


@router.post("/clubs", status_code=status.HTTP_201_CREATED)
def create_club(body: ClubIn, repo: Repo) -> ClubOut:
    return ClubOut.model_validate(services.create_club(repo, body.name))


@router.get("/clubs/{club_id}")
def get_club(club_id: UUID, repo: Repo) -> ClubDetail:
    club = services.club(repo, club_id)
    teams = [TeamRef(id=t.id, name=t.name) for t in repo.club_teams(club_id)]
    return ClubDetail(id=club.id, name=club.name, teams=teams)


# --- teams --------------------------------------------------------------------


@router.get("/teams")
def list_saved_teams(repo: Repo) -> list[TeamOut]:
    """The general base: saved teams, to enter into new competitions."""
    return [TeamOut.model_validate(t) for t in repo.saved_teams()]


@router.post("/teams", status_code=status.HTTP_201_CREATED)
def create_team(body: TeamIn, repo: Repo) -> TeamOut:
    row = services.create_team(repo, body.name, body.short_name, body.club_id, body.saved)
    return TeamOut.model_validate(row)


@router.get("/teams/{team_id}")
def get_team(team_id: UUID, repo: Repo) -> TeamOut:
    return TeamOut.model_validate(services.team(repo, team_id))


@router.patch("/teams/{team_id}")
def update_team(team_id: UUID, body: TeamPatch, repo: Repo) -> TeamOut:
    row = services.update_team(repo, team_id, body.model_dump(exclude_unset=True))
    return TeamOut.model_validate(row)


# --- competitions -------------------------------------------------------------


@router.get("/competitions")
def list_competitions(repo: Repo) -> list[CompetitionOut]:
    return [CompetitionOut.model_validate(c) for c in repo.competitions()]


@router.post("/competitions", status_code=status.HTTP_201_CREATED)
def create_competition(body: CompetitionIn, repo: Repo) -> CompetitionOut:
    row = services.create_competition(repo, body.slug, body.name, body.preset, body.timezone)
    return CompetitionOut.model_validate(row)


@router.get("/competitions/{slug}")
def get_competition(slug: str, repo: Repo) -> CompetitionOut:
    return CompetitionOut.model_validate(services.competition(repo, slug))


@router.get("/competitions/{slug}/teams")
def list_competition_teams(slug: str, repo: Repo) -> list[TeamOut]:
    comp = services.competition(repo, slug)
    return [TeamOut.model_validate(t) for t in repo.competition_teams(comp.id)]


@router.post("/competitions/{slug}/teams", status_code=status.HTTP_201_CREATED)
def enter_team(slug: str, body: EntryIn, repo: Repo) -> TeamOut:
    services.competition(repo, slug)
    if body.team is not None:
        new = body.team
        team_id = services.create_team(repo, new.name, new.short_name, new.club_id, new.saved).id
    else:
        assert body.team_id is not None
        team_id = body.team_id
    services.enter_team(repo, slug, team_id)
    return TeamOut.model_validate(services.team(repo, team_id))


@router.post("/competitions/{slug}/fixtures", status_code=status.HTTP_201_CREATED)
def generate_fixtures(slug: str, body: FixturesIn, repo: Repo) -> list[MatchOut]:
    matches = services.generate_fixtures(repo, slug, body.double)
    return _match_list(repo, slug, matches)


@router.get("/competitions/{slug}/matches")
def list_matches(slug: str, repo: Repo) -> list[MatchOut]:
    comp = services.competition(repo, slug)
    return _match_list(repo, slug, repo.matches(comp.id))


@router.get("/competitions/{slug}/standings")
def get_standings(slug: str, repo: Repo) -> list[StandingOut]:
    rows = services.standings(repo, slug)
    names = _team_names(repo, slug)
    return [_standing_out(row, names) for row in rows]


# --- matches ------------------------------------------------------------------


@router.get("/matches/{match_id}")
def get_match(match_id: UUID, repo: Repo) -> MatchOut:
    comp, match = services.match(repo, match_id)
    return _match_out(match, _team_names(repo, comp.slug))


@router.post("/matches/{match_id}/reschedule")
def reschedule(match_id: UUID, body: RescheduleIn, repo: Repo) -> MatchOut:
    return _changed(repo, match_id, lambda m, _: edits.reschedule(m, body.starts_at, body.venue))


@router.post("/matches/{match_id}/postpone")
def postpone(match_id: UUID, repo: Repo) -> MatchOut:
    return _changed(repo, match_id, lambda m, _: edits.postpone(m))


@router.post("/matches/{match_id}/cancel")
def cancel(match_id: UUID, repo: Repo) -> MatchOut:
    return _changed(repo, match_id, lambda m, _: edits.cancel(m))


@router.post("/matches/{match_id}/result")
def record_result(match_id: UUID, body: ResultIn, repo: Repo) -> MatchOut:
    sets = [SetScore(s.home, s.away) for s in body.sets]
    return _changed(repo, match_id, lambda m, rules: edits.record_result(m, sets, rules))


@router.post("/matches/{match_id}/walkover")
def record_walkover(match_id: UUID, body: WalkoverIn, repo: Repo) -> MatchOut:
    return _changed(repo, match_id, lambda m, _: edits.record_walkover(m, str(body.winner)))


@router.get("/matches/{match_id}/events")
def list_events(match_id: UUID, repo: Repo) -> list[EventOut]:
    services.match(repo, match_id)
    return [_event_out(repo, e) for e in repo.events(match_id)]


@router.post("/matches/{match_id}/events", status_code=status.HTTP_201_CREATED)
def add_event(match_id: UUID, body: EventIn, repo: Repo) -> EventOut:
    row = services.add_event(repo, match_id, body.team_id, body.player_id, body.stat, body.value)
    return _event_out(repo, row)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: UUID, repo: Repo) -> None:
    services.delete_event(repo, event_id)


# --- players and rosters ------------------------------------------------------


@router.post("/players", status_code=status.HTTP_201_CREATED)
def create_player(body: PlayerIn, repo: Repo) -> PlayerOut:
    return PlayerOut.model_validate(services.create_player(repo, body.first_name, body.last_name))


@router.get("/players/{player_id}")
def get_player(player_id: UUID, repo: Repo) -> PlayerOut:
    return PlayerOut.model_validate(services.player(repo, player_id))


@router.patch("/players/{player_id}")
def update_player(player_id: UUID, body: PlayerPatch, repo: Repo) -> PlayerOut:
    row = services.update_player(repo, player_id, body.first_name, body.last_name)
    return PlayerOut.model_validate(row)


@router.get("/competitions/{slug}/teams/{team_id}/roster")
def get_roster(slug: str, team_id: UUID, repo: Repo) -> list[RosterEntryOut]:
    """Current and past roster entries (past ones have `left_on`)."""
    comp = services.team_in_competition(repo, slug, team_id)
    return [_entry_out(e, p) for e, p in repo.roster_entries(comp.id, team_id)]


@router.post("/competitions/{slug}/teams/{team_id}/roster", status_code=status.HTTP_201_CREATED)
def join_roster(slug: str, team_id: UUID, body: RosterIn, repo: Repo) -> RosterEntryOut:
    services.competition(repo, slug)
    if body.player is not None:
        player_id = services.create_player(repo, body.player.first_name, body.player.last_name).id
    else:
        assert body.player_id is not None
        player_id = body.player_id
    entry = services.join_roster(
        repo, slug, team_id, player_id, body.number, body.position, body.joined_on
    )
    return _entry_out(entry, services.player(repo, player_id))


@router.post("/roster-entries/{entry_id}/leave")
def leave_roster(entry_id: UUID, body: LeaveIn, repo: Repo) -> RosterEntryOut:
    entry = services.leave_roster(repo, entry_id, body.left_on)
    return _entry_out(entry, services.player(repo, entry.player_id))


@router.get("/competitions/{slug}/stats")
def get_player_stats(slug: str, repo: Repo) -> list[PlayerStatsOut]:
    """Statistic totals per player, by last name."""
    comp = services.competition(repo, slug)
    totals = services.player_stats(repo, slug)
    names = _team_names(repo, slug)
    players: dict[str, PlayerRow] = {}  # in roster order, i.e. by last name
    current_team: dict[str, TeamRef] = {}
    for entry, player in repo.roster_entries(comp.id):
        players[str(player.id)] = player
        if entry.left_on is None:
            current_team[str(player.id)] = _ref(str(entry.team_id), names)
    return [
        PlayerStatsOut(player=_player_ref(p), team=current_team.get(pid), stats=totals[pid])
        for pid, p in players.items()
        if pid in totals
    ]


# --- response building --------------------------------------------------------


def _team_names(repo: Repository, slug: str) -> dict[str, str]:
    comp = services.competition(repo, slug)
    return {str(t.id): t.name for t in repo.competition_teams(comp.id)}


def _ref(team_id: str, names: dict[str, str]) -> TeamRef:
    return TeamRef(id=UUID(team_id), name=names[team_id])


def _match_out(match: Match, names: dict[str, str]) -> MatchOut:
    assert match.id is not None
    return MatchOut(
        id=match.id,
        round=match.round,
        home=_ref(match.home, names),
        away=_ref(match.away, names),
        status=match.status,
        starts_at=match.starts_at,
        venue=match.venue,
        sets=[SetOut(home=s.home, away=s.away) for s in match.sets],
        walkover_winner=UUID(match.walkover_winner) if match.walkover_winner else None,
    )


def _match_list(repo: Repository, slug: str, matches: list[Match]) -> list[MatchOut]:
    names = _team_names(repo, slug)
    return [_match_out(m, names) for m in matches]


def _changed(repo: Repository, match_id: UUID, change: services.MatchChange) -> MatchOut:
    match = services.change_match(repo, match_id, change)
    comp, _ = services.match(repo, match_id)
    return _match_out(match, _team_names(repo, comp.slug))


def _standing_out(row: StandingRow, names: dict[str, str]) -> StandingOut:
    return StandingOut(
        position=row.position,
        team=_ref(row.team, names),
        played=row.played,
        wins=row.wins,
        losses=row.losses,
        points=row.points,
        sets_won=row.sets_won,
        sets_lost=row.sets_lost,
        small_points_won=row.small_points_won,
        small_points_lost=row.small_points_lost,
    )


def _player_ref(player: PlayerRow) -> PlayerRef:
    return PlayerRef(id=player.id, name=f"{player.first_name} {player.last_name}")


def _entry_out(entry: RosterEntryRow, player: PlayerRow) -> RosterEntryOut:
    return RosterEntryOut(
        id=entry.id,
        team_id=entry.team_id,
        player=PlayerOut.model_validate(player),
        number=entry.number,
        position=entry.position,
        joined_on=entry.joined_on,
        left_on=entry.left_on,
    )


def _event_out(repo: Repository, event: MatchEventRow) -> EventOut:
    return EventOut(
        id=event.id,
        team_id=event.team_id,
        player=_player_ref(services.player(repo, event.player_id)),
        stat=event.stat,
        value=event.value,
    )
