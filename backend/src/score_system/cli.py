"""Command-line tools.

`score seed` loads a sample volleyball league, and a finished season ready for its
play-off, into the database.
`score openapi` prints the API v1 schema (the snapshot kept in backend/openapi.json).
`score export` writes the static JSON snapshot of the public API (see api/export.py).
"""

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from score_system.domain.fixtures import round_robin
from score_system.domain.matches import record_result, record_walkover, reschedule
from score_system.domain.models import MatchStatus, SetScore
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
# A finished regular season of 10 teams with the TAURON Liga play-off not started yet.
PLAYOFF_SLUG = "sample-playoff-league"
PLAYOFF_TEAMS = [f"Play-off Team {i}" for i in range(1, 11)]


def seed(session: Session) -> bool:
    """Create the sample league: a club, six teams with players, fixtures, two rounds of
    results and some player statistics.

    Also creates the play-off sample (see `seed_playoff`). Returns False and changes
    nothing if both already exist.
    """
    repo = Repository(session)
    created_playoff = seed_playoff(repo)
    if repo.competition_by_slug(SAMPLE_SLUG) is not None:
        return created_playoff

    rules = load_preset("volleyball")
    competition_id = repo.add_competition(SAMPLE_SLUG, "Sample Volleyball League", "volleyball")
    club_id = repo.add_club(SAMPLE_CLUB)
    team_ids = []
    players: dict[UUID, list[UUID]] = {}
    for name in SAMPLE_TEAMS:
        club = club_id if name.startswith("Eagles") else None
        team_id = repo.add_team(name, club_id=club, saved=True)
        repo.enter_team(competition_id, team_id)
        team_ids.append(str(team_id))
        # Two players per team, e.g. "Eagles Player 1", with a number and a position.
        for number, position in [(1, "setter"), (7, "outside hitter")]:
            player_id = repo.add_player(name, f"Player {number}")
            repo.add_roster_entry(competition_id, team_id, player_id, number, position, None)
            players.setdefault(team_id, []).append(player_id)

    # Rounds 1-2 are played (one match of round 2 as a walkover), the rest is scheduled
    # weekly on Friday evenings.
    for i, match in enumerate(round_robin(team_ids)):
        if match.round <= 2:
            match = record_result(match, SAMPLE_SCORES[i % len(SAMPLE_SCORES)], rules)
        if match.round == 2 and i % 3 == 0:
            match = record_walkover(match, match.away)
        if match.round > 2:
            match = reschedule(match, FIRST_FRIDAY + timedelta(weeks=match.round - 3), "City Hall")
        stored = repo.save_match(competition_id, match)
        if stored.status == MatchStatus.PLAYED and stored.id is not None:
            # Points of each team's outside hitter.
            for team in (stored.home, stored.away):
                hitter = players[UUID(team)][1]
                repo.add_event(stored.id, UUID(team), hitter, "points_scored", 12 + i)
    return True


def seed_playoff(repo: Repository) -> bool:
    """A finished single round robin of 10 teams with the TAURON Liga play-off format, so
    the play-off can be started right away. The team listed first wins every match (3:0
    or 3:1), so the table is the team order. False if it already exists."""
    if repo.competition_by_slug(PLAYOFF_SLUG) is not None:
        return False
    rules = load_preset("volleyball")
    competition_id = repo.add_competition(
        PLAYOFF_SLUG, "Sample Play-off League", "volleyball", playoff="tauron-liga"
    )
    team_ids = []
    for name in PLAYOFF_TEAMS:
        team_id = repo.add_team(name)
        repo.enter_team(competition_id, team_id)
        team_ids.append(str(team_id))
    rank = {team: i for i, team in enumerate(team_ids)}
    for i, match in enumerate(round_robin(team_ids)):
        won = SAMPLE_SCORES[i % 2]  # 3:0 or 3:1, so 3 points a win and the table is clear
        home_wins = rank[match.home] < rank[match.away]
        sets = won if home_wins else [SetScore(s.away, s.home) for s in won]
        start = FIRST_FRIDAY - timedelta(weeks=10 - match.round)
        repo.save_match(competition_id, record_result(reschedule(match, start), sets, rules))
    return True


def openapi_json() -> str:
    from score_system.api.main import app  # imported here: only this command needs it

    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="score")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="load the sample volleyball league")
    commands.add_parser("openapi", help="print the OpenAPI schema as JSON")
    export = commands.add_parser("export", help="write the static JSON snapshot")
    export.add_argument("--out", type=Path, default=Path("data/export"), help="target directory")
    args = parser.parse_args()

    if args.command == "openapi":
        sys.stdout.write(openapi_json())
        return
    if args.command == "export":
        from score_system.api.export import export as export_snapshot  # only this command

        with Session(make_engine()) as session:
            count = export_snapshot(Repository(session), args.out)
        print(f"Wrote {count} files to {args.out / 'api' / 'v1'}.")
        return
    with Session(make_engine()) as session:
        if seed(session):
            session.commit()
            print(f"Created the samples {SAMPLE_SLUG!r} and {PLAYOFF_SLUG!r}.")
        else:
            print("The samples already exist, nothing to do.")
