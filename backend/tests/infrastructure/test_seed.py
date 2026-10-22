from sqlalchemy import select
from sqlalchemy.orm import Session

from score_system.application import services
from score_system.cli import (
    PLAYOFF_SLUG,
    PLAYOFF_TEAMS,
    SAMPLE_CLUB,
    SAMPLE_SLUG,
    SAMPLE_TEAMS,
    seed,
)
from score_system.domain.matches import standings_results
from score_system.domain.models import MatchStatus
from score_system.domain.standings import compute_standings
from score_system.infrastructure.orm import ClubRow
from score_system.infrastructure.presets import load_preset
from score_system.infrastructure.repository import Repository


def test_seed_creates_sample_league_once(session: Session) -> None:
    assert seed(session) is True
    assert seed(session) is False

    repo = Repository(session)
    competition = repo.competition_by_slug(SAMPLE_SLUG)
    assert competition is not None
    teams = [str(t.id) for t in repo.competition_teams(competition.id)]
    matches = repo.matches(competition.id)
    assert len(teams) == len(SAMPLE_TEAMS) and len(matches) == 15
    statuses = {m.status for m in matches}
    assert statuses == {MatchStatus.PLAYED, MatchStatus.WALKOVER, MatchStatus.SCHEDULED}

    rules = load_preset(competition.preset)
    rows = compute_standings(teams, standings_results(matches, rules), rules)
    assert sum(r.played for r in rows) == 2 * 6  # two rounds of three matches

    club = session.scalars(select(ClubRow).where(ClubRow.name == SAMPLE_CLUB)).one()
    assert [t.name for t in repo.club_teams(club.id)] == ["Eagles", "Eagles II"]

    assert len(repo.roster_entries(competition.id)) == 2 * len(SAMPLE_TEAMS)
    assert len(repo.competition_events(competition.id)) == 2 * 5  # two per played match


def test_seed_creates_a_season_ready_for_its_play_off(session: Session) -> None:
    seed(session)
    repo = Repository(session)
    comp = services.competition(repo, PLAYOFF_SLUG)

    table = services.standings(repo, comp)
    assert [r.played for r in table] == [9] * 10
    names = services.team_names(repo, comp)
    assert [names[r.team] for r in table] == PLAYOFF_TEAMS
    assert services.playoff(repo, comp).started is False

    started = services.start_playoff(repo, comp)
    assert (names[started.series["A"].high or ""], names[started.series["A"].low or ""]) == (
        "Play-off Team 1",
        "Play-off Team 8",
    )
