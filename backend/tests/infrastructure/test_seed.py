from sqlalchemy import select
from sqlalchemy.orm import Session

from score_system.cli import SAMPLE_CLUB, SAMPLE_SLUG, SAMPLE_TEAMS, seed
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
