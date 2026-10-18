from collections.abc import Sequence

from score_system.domain.errors import DomainError
from score_system.domain.models import Match


def round_robin(teams: Sequence[str], double: bool = False) -> list[Match]:
    """Every team plays every other team once (twice when `double`, home and away swapped).

    Circle method (Berger tables): team positions rotate around a fixed one, so every pair
    meets exactly once in n - 1 rounds. With an odd number of teams, one team rests each
    round. Home and away alternate, so each team's home and away counts differ by at most
    one and, within a leg, no team plays more than two home or away matches in a row.
    """
    if len(teams) < 2:
        raise DomainError("a round robin needs at least two teams")
    if len(set(teams)) != len(teams):
        raise DomainError("team identifiers must be unique")

    # With an odd number of teams, index len(teams) is a "rest" slot paired with a real team.
    n = len(teams) + len(teams) % 2
    fixed = n - 1
    first_leg: list[Match] = []
    for r in range(n - 1):
        pairs = [(fixed, r) if r % 2 else (r, fixed)]
        for i in range(1, n // 2):
            a, b = (r + i) % fixed, (r - i) % fixed
            pairs.append((b, a) if i % 2 else (a, b))
        first_leg += [
            Match(round=r + 1, home=teams[h], away=teams[a])
            for h, a in pairs
            if h < len(teams) and a < len(teams)
        ]

    if not double:
        return first_leg
    second_leg = [Match(round=m.round + n - 1, home=m.away, away=m.home) for m in first_leg]
    return first_leg + second_leg
