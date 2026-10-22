"""Play-off: series between teams placed by the regular-season table.

A format (a YAML file in backend/presets/playoffs/) names each series and where its teams
come from: a regular-season place ("seed 1"), or the winner or loser of an earlier series.
A series between more than two sources ("the losers of A-D") is played by the two
best-seeded of them; the others are its "rest". A series is won by the first team to win
`wins` games; the better-seeded team hosts game 1, then the host alternates.

The state of the play-off is always derived from the seeds and the games played, never
stored, just like the standings.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from score_system.domain.errors import DomainError
from score_system.domain.models import Match, MatchStatus

_REF = re.compile(r"^(seed) ([1-9][0-9]*)$|^(winner|loser|rest) ([A-Za-z0-9]+)$")


def _parse(ref: str) -> tuple[str, str]:
    """("seed", "1"), ("winner", "A"), ...; ValueError for anything else."""
    found = _REF.match(ref)
    if found is None:
        raise ValueError(f"not a team source: {ref!r} (seed N, winner X, loser X, rest X)")
    kind, name = (found[1], found[2]) if found[1] else (found[3], found[4])
    return kind, name


class SeriesFormat(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Where the teams come from; with more than two, the two best-seeded play.
    sides: list[str] = Field(min_length=2)
    wins: PositiveInt  # games needed to win the series


class PlayoffFormat(BaseModel):
    """A fixed play-off format, chosen when a competition is created."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    seeds: PositiveInt  # the top `seeds` teams of the regular season take part
    # In playing order: a series may only use the results of series listed before it.
    series: dict[str, SeriesFormat]
    # Final places 1..seeds; places below come from the regular-season table.
    places: list[str]

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        seeds: list[int] = []
        known: dict[str, SeriesFormat] = {}
        for key, series in self.series.items():
            for ref in series.sides:
                kind, name = _parse(ref)
                if kind == "seed":
                    seeds.append(int(name))
                elif kind == "rest" or name not in known:
                    raise ValueError(f"series {key}: {ref!r} is not an earlier series' result")
            known[key] = series
        if sorted(seeds) != list(range(1, self.seeds + 1)):
            raise ValueError(f"seeds 1-{self.seeds} must each start exactly one series")

        # Every team ends in exactly one place: each series gives a winner and a loser,
        # and each of its rest teams.
        available = {f"{kind} {key}" for key in self.series for kind in ("winner", "loser")}
        rest = {key: len(s.sides) - 2 for key, s in self.series.items()}
        used_as_side = {ref for s in self.series.values() for ref in s.sides}
        for ref in self.places:
            kind, name = _parse(ref)
            if kind == "rest" and rest.get(name, 0) > 0:
                rest[name] -= 1
            elif ref in available and ref not in used_as_side:
                available.remove(ref)
            else:
                raise ValueError(f"place {ref!r} is not a final result or is used twice")
        if len(self.places) != self.seeds:
            raise ValueError(f"places must list exactly {self.seeds} final places")
        return self


@dataclass(frozen=True)
class Series:
    """One series as it stands: its teams (once known) and the games won by each."""

    key: str
    wins: int
    high: str | None = None  # the better-seeded team, host of the odd games
    low: str | None = None
    rest: tuple[str, ...] = ()  # sources that did not make it into the series, by seed
    high_wins: int = 0
    low_wins: int = 0

    @property
    def winner(self) -> str | None:
        if self.high_wins == self.wins:
            return self.high
        return self.low if self.low_wins == self.wins else None

    @property
    def loser(self) -> str | None:
        if self.winner is None:
            return None
        return self.low if self.winner == self.high else self.high


def series_states(
    fmt: PlayoffFormat, table: Sequence[str], games: Mapping[str, Sequence[Match]]
) -> dict[str, Series]:
    """Every series of the format, from the regular-season `table` (team ids, first place
    first) and the games played so far in each series (by series key)."""
    if len(table) < fmt.seeds:
        raise DomainError(f"the play-off needs {fmt.seeds} teams, the table has {len(table)}")
    rank = {team: i for i, team in enumerate(table)}
    states: dict[str, Series] = {}
    for key, series in fmt.series.items():
        sources = [_resolve(ref, table, states) for ref in series.sides]
        if any(team is None for team in sources):
            states[key] = Series(key, series.wins)
            continue
        high, low, *rest = sorted((t for t in sources if t is not None), key=rank.__getitem__)
        high_wins = low_wins = 0
        for game in games.get(key, ()):
            winner = _game_winner(game)
            if {game.home, game.away} != {high, low}:
                raise DomainError(f"a game of series {key} is not between {high} and {low}")
            high_wins += winner == high
            low_wins += winner == low
        if max(high_wins, low_wins) > series.wins:
            raise DomainError(f"series {key} has games after it was decided")
        states[key] = Series(key, series.wins, high, low, tuple(rest), high_wins, low_wins)
    return states


def games_to_add(states: Mapping[str, Series], games: Mapping[str, Sequence[Match]]) -> list[Match]:
    """Games the series still need scheduled.

    A series always has as many games as its leader still needs to win: best of three
    starts with two games and gets a third at 1:1. Game numbers go in `round`.
    """
    added = []
    for key, series in states.items():
        if series.high is None or series.low is None:
            continue
        existing = [g for g in games.get(key, ()) if g.status != MatchStatus.CANCELLED]
        for number in range(len(existing) + 1, _games_needed(series) + 1):
            home, away = (series.high, series.low) if number % 2 else (series.low, series.high)
            added.append(Match(round=number, home=home, away=away, series=key))
    return added


def surplus_games(
    states: Mapping[str, Series], games: Mapping[str, Sequence[Match]]
) -> list[Match]:
    """Unplayed games no longer needed, e.g. after a corrected result decided a series."""
    surplus = []
    for key, series in states.items():
        needed = _games_needed(series)
        surplus += [
            g
            for g in games.get(key, ())
            if g.round > needed and g.status in (MatchStatus.SCHEDULED, MatchStatus.POSTPONED)
        ]
    return surplus


def _games_needed(series: Series) -> int:
    if series.high is None:
        return 0
    leader = max(series.high_wins, series.low_wins)
    return series.high_wins + series.low_wins + series.wins - leader


def final_places(
    fmt: PlayoffFormat, table: Sequence[str], states: Mapping[str, Series]
) -> list[str | None]:
    """The final classification: the play-off places (None until decided), then the
    other teams in their regular-season order."""
    rest_used: dict[str, int] = {}
    places: list[str | None] = []
    for ref in fmt.places:
        kind, key = _parse(ref)
        if kind == "rest":
            index = rest_used.get(key, 0)
            rest_used[key] = index + 1
            rest = states[key].rest
            places.append(rest[index] if index < len(rest) else None)
        else:
            places.append(_resolve(ref, table, states))
    return places + list(table[fmt.seeds :])


def _resolve(ref: str, table: Sequence[str], states: Mapping[str, Series]) -> str | None:
    kind, name = _parse(ref)
    if kind == "seed":
        return table[int(name) - 1]
    series = states[name]
    return series.winner if kind == "winner" else series.loser


def _game_winner(game: Match) -> str | None:
    """The winner of a finished game; None while it is not played."""
    if game.status == MatchStatus.WALKOVER:
        return game.walkover_winner
    if game.status != MatchStatus.PLAYED:
        return None
    home_sets = sum(1 for s in game.sets if s.home > s.away)
    return game.home if home_sets * 2 > len(game.sets) else game.away
