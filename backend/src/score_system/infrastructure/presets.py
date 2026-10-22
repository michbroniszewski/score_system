from functools import cache
from pathlib import Path

import yaml

from score_system.domain.playoff import PlayoffFormat
from score_system.domain.rules import RuleSet


def load_ruleset(path: Path) -> RuleSet:
    return RuleSet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


# backend/presets/ (locally) or /app/presets/ (in the Docker image).
PRESETS_DIR = Path(__file__).resolve().parents[3] / "presets"


# Presets are read once per process (RuleSet is immutable); restart the API after editing one.
@cache
def load_preset(name: str) -> RuleSet:
    return load_ruleset(PRESETS_DIR / f"{name}.yaml")


@cache
def preset_names() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in PRESETS_DIR.glob("*.yaml")))


PLAYOFFS_DIR = PRESETS_DIR / "playoffs"


def load_playoff_file(path: Path) -> PlayoffFormat:
    return PlayoffFormat.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


# Play-off formats are fixed: chosen when a competition is created, never edited.
@cache
def load_playoff(name: str) -> PlayoffFormat:
    return load_playoff_file(PLAYOFFS_DIR / f"{name}.yaml")


@cache
def playoff_names() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in PLAYOFFS_DIR.glob("*.yaml")))
