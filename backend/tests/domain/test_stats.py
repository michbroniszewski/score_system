import pytest

from score_system.domain.models import StatEvent
from score_system.domain.rules import RuleSet
from score_system.domain.stats import player_totals


def test_totals_per_player(volleyball: RuleSet) -> None:
    events = [
        StatEvent("anna", "aces", 2),
        StatEvent("anna", "aces", 1),
        StatEvent("anna", "points_scored", 15),
        StatEvent("ola", "mvp"),
    ]

    totals = player_totals(events, volleyball)

    assert totals == {
        "anna": {"points_scored": 15, "aces": 3, "blocks": 0, "mvp": 0},
        "ola": {"points_scored": 0, "aces": 0, "blocks": 0, "mvp": 1},
    }


def test_unknown_statistic_is_rejected(volleyball: RuleSet) -> None:
    with pytest.raises(ValueError):
        player_totals([StatEvent("anna", "goals")], volleyball)
