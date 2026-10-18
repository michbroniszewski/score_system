from pathlib import Path

import yaml

from score_system.domain.rules import RuleSet


def load_ruleset(path: Path) -> RuleSet:
    return RuleSet.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
