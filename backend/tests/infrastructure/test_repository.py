from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from score_system.domain.fixtures import round_robin
from score_system.domain.matches import record_result, record_walkover, reschedule
from score_system.domain.models import Match, MatchStatus, SetScore
from score_system.domain.rules import RuleSet
from score_system.infrastructure.orm import TeamRow
from score_system.infrastructure.repository import Repository


@pytest.fixture
def repo(session: Session) -> Repository:
    return Repository(session)


def test_competition_with_teams(repo: Repository) -> None:
    competition_id = repo.add_competition("league", "League", "volleyball")
    for name in ["Owls", "Eagles"]:
        repo.enter_team(competition_id, repo.add_team(name))

    stored = repo.competition_by_slug("league")
    assert stored is not None and (stored.id, stored.preset) == (competition_id, "volleyball")
    assert [t.name for t in repo.competition_teams(competition_id)] == ["Eagles", "Owls"]
    assert repo.competition_by_slug("missing") is None


def test_match_round_trip(repo: Repository, volleyball: RuleSet) -> None:
    competition_id = repo.add_competition("league", "League", "volleyball")
    home, away = (str(repo.add_team(name)) for name in ["A", "B"])
    friday = datetime(2026, 11, 6, 19, 0, tzinfo=UTC)

    stored = repo.save_match(competition_id, reschedule(Match(1, home, away), friday, "Hall"))
    played = repo.save_match(
        competition_id, record_result(stored, [SetScore(25, 20)] * 3, volleyball)
    )

    assert stored.id is not None and played.id == stored.id
    assert repo.matches(competition_id) == [played]
    assert played.status == MatchStatus.PLAYED
    assert played.sets == (SetScore(25, 20),) * 3
    assert (played.starts_at, played.venue) == (friday, "Hall")


def test_walkover_round_trip(repo: Repository) -> None:
    competition_id = repo.add_competition("league", "League", "volleyball")
    home, away = (str(repo.add_team(name)) for name in ["A", "B"])

    stored = repo.save_match(competition_id, record_walkover(Match(1, home, away), away))

    assert repo.matches(competition_id) == [stored]
    assert (stored.status, stored.walkover_winner) == (MatchStatus.WALKOVER, away)


def test_fixtures_are_listed_by_round(repo: Repository) -> None:
    competition_id = repo.add_competition("league", "League", "volleyball")
    teams = [str(repo.add_team(name)) for name in ["A", "B", "C", "D"]]
    for match in reversed(round_robin(teams)):
        repo.save_match(competition_id, match)

    rounds = [m.round for m in repo.matches(competition_id)]
    assert rounds == sorted(rounds) and len(rounds) == 6


def test_duplicate_slug_is_rejected(repo: Repository) -> None:
    repo.add_competition("league", "League", "volleyball")
    with pytest.raises(IntegrityError):
        repo.add_competition("league", "Other", "volleyball")


def test_club_fields_several_teams(repo: Repository) -> None:
    club = repo.add_club("Eagles VC")
    first, second = repo.add_team("Eagles", club_id=club), repo.add_team("Eagles II", club_id=club)
    league = repo.add_competition("league", "League", "volleyball")
    cup = repo.add_competition("cup", "Cup", "volleyball")
    repo.enter_team(league, first)
    repo.enter_team(league, second)
    repo.enter_team(cup, first)

    assert [t.name for t in repo.club_teams(club)] == ["Eagles", "Eagles II"]
    assert [t.name for t in repo.competition_teams(league)] == ["Eagles", "Eagles II"]
    assert [t.name for t in repo.competition_teams(cup)] == ["Eagles"]


def test_team_without_club(repo: Repository) -> None:
    team = repo.add_team("Independents")

    assert repo.session.get_one(TeamRow, team).club_id is None


@pytest.mark.parametrize("add", [Repository.add_team, Repository.add_club])
def test_names_are_unique(repo: Repository, add: Callable[[Repository, str], UUID]) -> None:
    add(repo, "Eagles")
    with pytest.raises(IntegrityError):
        add(repo, "Eagles")


def test_match_start_is_read_in_utc(repo: Repository, session: Session) -> None:
    competition_id = repo.add_competition("league", "League", "volleyball")
    home, away = (str(repo.add_team(name)) for name in ["A", "B"])
    friday = datetime(2026, 11, 6, 19, 0, tzinfo=UTC)
    repo.save_match(competition_id, reschedule(Match(1, home, away), friday))
    session.execute(text("SET TIME ZONE 'Europe/Warsaw'"))
    session.expire_all()

    (stored,) = repo.matches(competition_id)

    assert stored.starts_at == friday and stored.starts_at.tzinfo is UTC


def test_a_match_cannot_move_to_another_competition(repo: Repository) -> None:
    league = repo.add_competition("league", "League", "volleyball")
    cup = repo.add_competition("cup", "Cup", "volleyball")
    home, away = (str(repo.add_team(name)) for name in ["A", "B"])
    stored = repo.save_match(league, Match(1, home, away))

    with pytest.raises(ValueError, match="another competition"):
        repo.save_match(cup, stored)
