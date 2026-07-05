"""Shared 1X2 domain vocabulary - no ML/DB/ingest dependencies.

Moved out of ml/ so predictions/ and betting/ (both consumers of "what is a
match outcome", not of any model-training machinery) don't couple to the ML
layer just to get an enum and a probability triple.
"""

from __future__ import annotations

from dataclasses import dataclass

RESULT_CLASSES: tuple[str, str, str] = ("HOME", "DRAW", "AWAY")


def result_from_goals(home_goals: int, away_goals: int) -> str:
    """Map a final score to a 1X2 label."""
    if home_goals > away_goals:
        return "HOME"
    if home_goals < away_goals:
        return "AWAY"
    return "DRAW"


@dataclass(frozen=True)
class MatchProbs:
    """Calibrated 1X2 probabilities for a single match."""

    home: float
    draw: float
    away: float

    def as_tuple(self) -> tuple[float, float, float]:
        """Return probabilities in (HOME, DRAW, AWAY) order."""
        return (self.home, self.draw, self.away)

    @property
    def confidence(self) -> float:
        """Confidence signal = the largest class probability."""
        return max(self.as_tuple())

    def __repr__(self) -> str:
        return f"<MatchProbs H={self.home:.3f} D={self.draw:.3f} A={self.away:.3f}>"
