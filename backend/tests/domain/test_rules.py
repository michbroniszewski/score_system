from typing import Any

import pytest
from pydantic import ValidationError

from score_system.domain.rules import RuleSet

VALID: dict[str, Any] = {
    "discipline": "volleyball",
    "result_format": "sets",
    "sets_to_win": 3,
    "points": {"3:0": [3, 0], "3:1": [3, 0], "3:2": [2, 1]},
    "tiebreakers": ["points", "wins"],
    "walkover_set": [25, 0],
}


def test_valid_ruleset() -> None:
    assert RuleSet.model_validate(VALID).points["3:2"] == (2, 1)


@pytest.mark.parametrize(
    "change",
    [
        {"points": {"3:0": [3, 0], "3:1": [3, 0]}},  # 3:2 missing
        {"points": {**VALID["points"], "3:3": [1, 1]}},  # impossible result
        {"sets_to_win": 2},  # points do not match best of three
        {"tiebreakers": ["points", "coin_toss"]},
        {"result_format": "score"},
        {"unexpected": 1},
        {"walkover_set": [0, 25]},  # winner must score more
        {"walkover_set": [25, 25]},
        {"walkover_set": [25, -1]},
        {"stats": ["aces", "aces"]},
    ],
)
def test_invalid_ruleset_is_rejected(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        RuleSet.model_validate({**VALID, **change})
