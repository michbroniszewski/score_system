import pytest

from score_system.domain.models import MatchResult, SetScore
from score_system.domain.results import InvalidResultError
from score_system.domain.rules import RuleSet
from score_system.domain.standings import compute_standings


def match(home: str, away: str, *sets: tuple[int, int]) -> MatchResult:
    return MatchResult(home, away, tuple(SetScore(h, a) for h, a in sets))


def test_no_matches_keeps_team_order(volleyball: RuleSet) -> None:
    rows = compute_standings(["A", "B"], [], volleyball)

    assert [(r.position, r.team, r.played, r.points) for r in rows] == [
        (1, "A", 0, 0),
        (2, "B", 0, 0),
    ]


@pytest.mark.parametrize(
    ("sets", "home_points", "away_points"),
    [
        ([(25, 20), (25, 20), (25, 20)], 3, 0),
        ([(25, 20), (20, 25), (25, 20), (25, 20)], 3, 0),
        ([(25, 20), (20, 25), (25, 20), (20, 25), (15, 10)], 2, 1),
        ([(20, 25), (25, 20), (20, 25), (25, 20), (10, 15)], 1, 2),
        ([(20, 25), (20, 25), (20, 25)], 0, 3),
    ],
)
def test_points_per_result(
    volleyball: RuleSet, sets: list[tuple[int, int]], home_points: int, away_points: int
) -> None:
    rows = compute_standings(["A", "B"], [match("A", "B", *sets)], volleyball)

    points = {r.team: r.points for r in rows}
    assert points == {"A": home_points, "B": away_points}


def test_row_counts_sets_and_small_points(volleyball: RuleSet) -> None:
    rows = compute_standings(
        ["A", "B"], [match("A", "B", (25, 20), (23, 25), (25, 18), (25, 22))], volleyball
    )

    a, b = rows
    assert (a.team, a.played, a.wins, a.losses, a.points) == ("A", 1, 1, 0, 3)
    assert (a.sets_won, a.sets_lost, a.small_points_won, a.small_points_lost) == (3, 1, 98, 85)
    assert (b.team, b.wins, b.losses, b.sets_won, b.sets_lost) == ("B", 0, 1, 1, 3)


FIVE_SETS_HOME_WIN = [(25, 20), (20, 25), (25, 20), (20, 25), (15, 10)]
FIVE_SETS_AWAY_WIN = [(20, 25), (25, 20), (20, 25), (25, 20), (10, 15)]


# A: two 3:2 wins = 4 pts, 2 wins, sets 6:4. B: 3:0 win + 2:3 loss = 4 pts, 1 win, sets 5:3.
EQUAL_POINTS_MORE_WINS_WORSE_SETS = [
    match("A", "C", *FIVE_SETS_HOME_WIN),
    match("A", "D", *FIVE_SETS_HOME_WIN),
    match("B", "C", *[(25, 20)] * 3),
    match("B", "D", *FIVE_SETS_AWAY_WIN),
]


def test_volleyball_ignores_wins(volleyball: RuleSet) -> None:
    rows = compute_standings(["A", "B", "C", "D"], EQUAL_POINTS_MORE_WINS_WORSE_SETS, volleyball)

    assert [(r.team, r.points, r.wins) for r in rows][:2] == [("B", 4, 1), ("A", 4, 2)]


def test_wins_break_points_tie_when_configured(volleyball: RuleSet) -> None:
    with_wins = volleyball.model_copy(update={"tiebreakers": ["points", "wins", "set_ratio"]})

    rows = compute_standings(["B", "A", "C", "D"], EQUAL_POINTS_MORE_WINS_WORSE_SETS, with_wins)

    assert [(r.team, r.points, r.wins) for r in rows][:2] == [("A", 4, 2), ("B", 4, 1)]


def test_set_ratio_breaks_tie(volleyball: RuleSet) -> None:
    # Both: one 3:0 win and one loss (3 pts, 1 win). A loses 0:3 (sets 3:3), B loses 1:3 (4:3).
    rows = compute_standings(
        ["A", "B", "C", "D"],
        [
            match("A", "C", *[(25, 20)] * 3),
            match("A", "D", *[(20, 25)] * 3),
            match("B", "C", *[(25, 20)] * 3),
            match("B", "D", (25, 20), (20, 25), (20, 25), (20, 25)),
        ],
        volleyball,
    )

    # D won both its matches and leads; B and A follow.
    assert [r.team for r in rows][:3] == ["D", "B", "A"]


def test_small_points_ratio_breaks_tie(volleyball: RuleSet) -> None:
    rows = compute_standings(
        ["A", "B", "C", "D"],
        [
            match("A", "C", *[(25, 23)] * 3),
            match("B", "D", *[(25, 10)] * 3),
        ],
        volleyball,
    )

    assert [r.team for r in rows][:2] == ["B", "A"]


def test_set_ratio_without_lost_sets_ranks_first(volleyball: RuleSet) -> None:
    # Equal points and wins; A lost no sets (ratio infinite), B lost one.
    rows = compute_standings(
        ["B", "A", "C", "D"],
        [
            match("A", "C", (25, 10), (25, 10), (25, 10)),
            match("B", "D", (25, 10), (10, 25), (25, 10), (25, 10)),
        ],
        volleyball,
    )

    assert [r.team for r in rows][:2] == ["A", "B"]


@pytest.mark.parametrize(
    "sets",
    [
        [],
        [(25, 20), (25, 20)],  # not finished
        [(25, 20), (25, 20), (25, 20), (25, 20)],  # set played after the match was won
        [(20, 25), (25, 20), (25, 20), (25, 20), (25, 20)],  # 4:1 is impossible
        [(25, 25), (25, 20), (25, 20), (25, 20)],  # set without a winner
        [(25, -1), (25, 20), (25, 20)],
    ],
)
def test_invalid_result_is_rejected(volleyball: RuleSet, sets: list[tuple[int, int]]) -> None:
    with pytest.raises(InvalidResultError):
        compute_standings(["A", "B"], [match("A", "B", *sets)], volleyball)


def test_unknown_team_is_rejected(volleyball: RuleSet) -> None:
    with pytest.raises(InvalidResultError):
        compute_standings(["A"], [match("A", "X", *[(25, 20)] * 3)], volleyball)


def test_team_cannot_play_itself(volleyball: RuleSet) -> None:
    with pytest.raises(InvalidResultError):
        compute_standings(["A"], [match("A", "A", *[(25, 20)] * 3)], volleyball)
