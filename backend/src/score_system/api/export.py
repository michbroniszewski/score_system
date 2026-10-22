"""Static export: the public GET responses of API v1, written as JSON files.

Each file holds exactly what the API answers at the same path plus ".json", e.g.
`api/v1/competitions/{slug}/standings.json` is GET /api/v1/competitions/{slug}/standings.
So the GitHub Pages site and the future mobile app read the snapshot and the live API the
same way. The responses are built by the route functions themselves, so the format cannot
drift from the API.
"""

import json
import shutil
from pathlib import Path
from typing import Any

from pydantic_core import to_jsonable_python

from score_system.api import routes
from score_system.application import services
from score_system.infrastructure.repository import Repository


def export(repo: Repository, out: Path) -> int:
    """Replace the snapshot in `out` with the current data; returns the number of files."""
    pages = _pages(repo)
    root = out / "api" / "v1"
    if root.exists():
        shutil.rmtree(root)  # no stale files of deleted competitions or matches
    for path, body in pages.items():
        file = root / f"{path}.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(to_jsonable_python(body), indent=2, ensure_ascii=False) + "\n"
        file.write_text(text, encoding="utf-8")
    return len(pages)


def _pages(repo: Repository) -> dict[str, Any]:
    """Response bodies by API path (relative to /api/v1/)."""
    pages: dict[str, Any] = {
        "presets": routes.list_presets(),
        "competitions": routes.list_competitions(repo),
    }
    for comp in services.competitions(repo):
        base = f"competitions/{comp.slug}"
        teams = routes.list_competition_teams(comp.slug, repo)
        matches = routes.list_matches(comp.slug, repo)
        pages[base] = routes.get_competition(comp.slug, repo)
        pages[f"{base}/teams"] = teams
        pages[f"{base}/matches"] = matches
        pages[f"{base}/standings"] = routes.get_standings(comp.slug, repo)
        pages[f"{base}/stats"] = routes.get_player_stats(comp.slug, repo)
        for team in teams:
            pages[f"{base}/teams/{team.id}/roster"] = routes.get_roster(comp.slug, team.id, repo)
        if comp.playoff is not None:
            playoff = routes.get_playoff(comp.slug, repo)
            pages[f"{base}/playoff"] = playoff
            matches = matches + [m for s in playoff.series for m in s.matches]
        for match in matches:
            pages[f"matches/{match.id}"] = match
            pages[f"matches/{match.id}/events"] = routes.list_events(match.id, repo)
    return pages
