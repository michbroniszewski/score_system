"""Command-line tools: `score seed` loads a sample volleyball league into the database."""

import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from score_system.domain.fixtures import round_robin
from score_system.domain.matches import record_result, record_walkover, reschedule
from score_system.domain.models import SetScore
from score_system.infrastructure.db import make_engine
from score_system.infrastructure.presets import load_preset
from score_system.infrastructure.repository import Repository

SAMPLE_SLUG = "sample-volleyball-league"
SAMPLE_CLUB = "Eagles VC"  # fields two of the sample teams
SAMPLE_TEAMS = ["Eagles", "Eagles II", "Falcons", "Hawks", "Owls", "Ravens"]
SAMPLE_SCORES = [
    [SetScore(25, 20), SetScore(25, 18), SetScore(25, 22)],
    [SetScore(25, 23), SetScore(22, 25), SetScore(25, 19), SetScore(25, 21)],
    [SetScore(20, 25), SetScore(25, 22), SetScore(23, 25), SetScore(25, 20), SetScore(15, 12)],
    [SetScore(19, 25), SetScore(21, 25), SetScore(25, 27)],
]
FIRST_FRIDAY = datetime(2026, 11, 6, 19, 0, tzinfo=UTC)


def seed(session: Session) -> bool:
    """Create the sample league: a club, six teams, fixtures and two rounds of results.

    Returns False and changes nothing if it already exists.
    """
    repo = Repository(session)
    if repo.competition_by_slug(SAMPLE_SLUG) is not None:
        return False

    rules = load_preset("volleyball")
    competition_id = repo.add_competition(SAMPLE_SLUG, "Sample Volleyball League", "volleyball")
    club_id = repo.add_club(SAMPLE_CLUB)
    team_ids = []
    for name in SAMPLE_TEAMS:
        team_id = repo.add_team(name, club_id=club_id if name.startswith("Eagles") else None)
        repo.enter_team(competition_id, team_id)
        team_ids.append(str(team_id))

    # Rounds 1-2 are played (one match of round 2 as a walkover), the rest is scheduled
    # weekly on Friday evenings.
    for i, match in enumerate(round_robin(team_ids)):
        if match.round <= 2:
            match = record_result(match, SAMPLE_SCORES[i % len(SAMPLE_SCORES)], rules)
        if match.round == 2 and i % 3 == 0:
            match = record_walkover(match, match.away)
        if match.round > 2:
            match = reschedule(match, FIRST_FRIDAY + timedelta(weeks=match.round - 3), "City Hall")
        repo.save_match(competition_id, match)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(prog="score")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="load the sample volleyball league")
    parser.parse_args()

    with Session(make_engine()) as session:
        if seed(session):
            session.commit()
            print(f"Created {SAMPLE_SLUG!r}.")
        else:
            print(f"{SAMPLE_SLUG!r} already exists, nothing to do.")
