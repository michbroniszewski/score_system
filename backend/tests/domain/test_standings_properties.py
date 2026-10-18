"""Property tests: invariants that must hold for any valid set of results."""

from random import Random

from hypothesis import given
from hypothesis import strategies as st

from score_system.domain.models import MatchResult, SetScore
from score_system.domain.rules import RuleSet
from score_system.domain.standings import compute_standings
from score_system.infrastructure.presets import load_ruleset
from tests.conftest import PRESETS

# Loaded once at import: hypothesis does not support function-scoped fixtures in @given tests.
VOLLEYBALL: RuleSet = load_ruleset(PRESETS / "volleyball.yaml")
TEAMS = ["A", "B", "C", "D", "E"]

winning_set = st.tuples(st.integers(25, 40), st.integers(0, 23))


@st.composite
def results(draw: st.DrawFn) -> MatchResult:
    home, away = draw(st.permutations(TEAMS))[:2]
    loser_sets = draw(st.integers(0, VOLLEYBALL.sets_to_win - 1))
    home_wins = draw(st.booleans())
    # The match winner's sets in random order, except the last set, which ends the match.
    winner_flags = draw(
        st.permutations([True] * (VOLLEYBALL.sets_to_win - 1) + [False] * loser_sets)
    )
    sets = []
    for winner_won_set in [*winner_flags, True]:
        high, low = draw(winning_set)
        home_won_set = winner_won_set == home_wins
        sets.append(SetScore(high, low) if home_won_set else SetScore(low, high))
    return MatchResult(home, away, tuple(sets))


def awarded_points(match: MatchResult) -> int:
    home_sets = sum(1 for s in match.sets if s.home > s.away)
    away_sets = len(match.sets) - home_sets
    key = f"{max(home_sets, away_sets)}:{min(home_sets, away_sets)}"
    return sum(VOLLEYBALL.points[key])


@given(st.lists(results(), max_size=30))
def test_totals_match_the_results(matches: list[MatchResult]) -> None:
    rows = compute_standings(TEAMS, matches, VOLLEYBALL)

    assert sum(r.points for r in rows) == sum(awarded_points(m) for m in matches)
    assert sum(r.wins for r in rows) == sum(r.losses for r in rows) == len(matches)
    assert sum(r.played for r in rows) == 2 * len(matches)
    assert sum(r.sets_won for r in rows) == sum(r.sets_lost for r in rows)
    assert sum(r.small_points_won for r in rows) == sum(r.small_points_lost for r in rows)


@given(st.lists(results(), max_size=30))
def test_rows_are_ranked_by_points(matches: list[MatchResult]) -> None:
    rows = compute_standings(TEAMS, matches, VOLLEYBALL)

    assert [r.position for r in rows] == list(range(1, len(TEAMS) + 1))
    assert sorted(r.team for r in rows) == sorted(TEAMS)
    points = [r.points for r in rows]
    assert points == sorted(points, reverse=True)


@given(st.lists(results(), max_size=30), st.randoms())
def test_match_order_does_not_matter(matches: list[MatchResult], rng: Random) -> None:
    shuffled = matches.copy()
    rng.shuffle(shuffled)

    assert compute_standings(TEAMS, shuffled, VOLLEYBALL) == compute_standings(
        TEAMS, matches, VOLLEYBALL
    )
