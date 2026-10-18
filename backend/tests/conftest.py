from pathlib import Path

import pytest

from score_system.domain.rules import RuleSet
from score_system.infrastructure.presets import load_ruleset

PRESETS = Path(__file__).parent.parent / "presets"


@pytest.fixture
def volleyball() -> RuleSet:
    return load_ruleset(PRESETS / "volleyball.yaml")
