from score_system.domain.rules import RuleSet


def test_volleyball_preset_loads(volleyball: RuleSet) -> None:
    assert volleyball.discipline == "volleyball"
    assert volleyball.sets_to_win == 3
    assert volleyball.points == {"3:0": (3, 0), "3:1": (3, 0), "3:2": (2, 1)}
    assert volleyball.tiebreakers == ["points", "set_ratio", "small_points_ratio"]
    assert volleyball.walkover_set == (25, 0)
    assert volleyball.stats == ["points_scored", "aces", "blocks", "mvp"]
