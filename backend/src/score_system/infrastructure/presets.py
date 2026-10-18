from pathlib import Path

import yaml

from score_system.domain.rules import RuleSet


def load_ruleset(path: Path) -> RuleSet:
    return RuleSet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


# backend/presets/ (locally) or /app/presets/ (in the Docker image).
PRESETS_DIR = Path(__file__).resolve().parents[3] / "presets"


def load_preset(name: str) -> RuleSet:
    return load_ruleset(PRESETS_DIR / f"{name}.yaml")


def preset_names() -> list[str]:
    return sorted(path.stem for path in PRESETS_DIR.glob("*.yaml"))
