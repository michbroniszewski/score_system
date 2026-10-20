import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from score_system.api.export import export
from score_system.cli import SAMPLE_SLUG, seed
from score_system.infrastructure.repository import Repository
from tests.api.helpers import API, get


def snapshot(out: Path) -> dict[str, str]:
    """Exported files by API path (relative to /api/v1/, without .json)."""
    root = out / "api" / "v1"
    return {
        f.relative_to(root).with_suffix("").as_posix(): f.read_text(encoding="utf-8")
        for f in sorted(root.rglob("*.json"))
    }


def test_every_exported_file_is_the_api_response(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    seed(session)

    count = export(Repository(session), tmp_path)

    files = snapshot(tmp_path)
    assert count == len(files)
    for path, text in files.items():
        assert json.loads(text) == get(client, f"/{path}"), path
    base = f"competitions/{SAMPLE_SLUG}"
    teams = get(client, f"/{base}/teams")
    matches = get(client, f"/{base}/matches")
    assert {
        "presets",
        "competitions",
        base,
        f"{base}/teams",
        f"{base}/matches",
        f"{base}/standings",
        f"{base}/stats",
        *(f"{base}/teams/{t['id']}/roster" for t in teams),
        *(f"matches/{m['id']}" for m in matches),
        *(f"matches/{m['id']}/events" for m in matches),
    } == set(files)
    assert client.get(f"{API}/{base}/stats").json() != []


def test_export_replaces_the_previous_snapshot(session: Session, tmp_path: Path) -> None:
    seed(session)
    stale = tmp_path / "api" / "v1" / "competitions" / "deleted.json"
    stale.parent.mkdir(parents=True)
    stale.write_text("{}")
    keep = tmp_path / "README.md"  # files outside api/ are left alone
    keep.write_text("notes")

    export(Repository(session), tmp_path)
    first = snapshot(tmp_path)
    export(Repository(session), tmp_path)

    assert not stale.exists() and keep.exists()
    assert snapshot(tmp_path) == first  # the same data gives the same files
