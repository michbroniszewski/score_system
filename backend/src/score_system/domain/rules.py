from typing import Literal

from pydantic import BaseModel, ConfigDict, PositiveInt, model_validator

from score_system.domain.tiebreakers import TIEBREAKERS


class RuleSet(BaseModel):
    """Competition rules of a discipline, loaded from a YAML preset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    discipline: str
    result_format: Literal["sets"]
    sets_to_win: PositiveInt
    # Set result "winner:loser" (e.g. "3:1") -> (winner points, loser points).
    points: dict[str, tuple[int, int]]
    tiebreakers: list[str]

    @model_validator(mode="after")
    def _check_consistency(self) -> "RuleSet":
        expected = {f"{self.sets_to_win}:{lost}" for lost in range(self.sets_to_win)}
        if set(self.points) != expected:
            raise ValueError(f"points must define exactly the results {sorted(expected)}")
        unknown = [name for name in self.tiebreakers if name not in TIEBREAKERS]
        if unknown:
            raise ValueError(f"unknown tiebreakers: {unknown}")
        return self
