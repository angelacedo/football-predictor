"""Value detection: compare model probabilities to bookmaker odds.

A bet has positive *edge* when the model thinks an outcome is more likely than the
odds imply: ``edge = model_prob * decimal_odds - 1``. We select the single outcome
with the largest edge, if it clears the threshold.

Example:
    >>> from footy.ml.predict import MatchProbs
    >>> bet = find_value_bet(MatchProbs(0.6, 0.25, 0.15), (2.0, 3.5, 5.0), threshold=0.05)
    >>> bet.selection, round(bet.edge, 2)
    ('HOME', 0.2)
    >>> find_value_bet(MatchProbs(0.4, 0.3, 0.3), (2.0, 3.5, 3.0), threshold=0.05) is None
    True
"""

from __future__ import annotations

from dataclasses import dataclass

from footy.ml.features import RESULT_CLASSES
from footy.ml.predict import MatchProbs

Odds = tuple[float, float, float]  # (home, draw, away) decimal odds


@dataclass(frozen=True)
class ValueBet:
    """A selected value bet (paper only — never placed)."""

    selection: str  # HOME | DRAW | AWAY
    model_prob: float
    market_odds: float
    edge: float

    def __repr__(self) -> str:
        return f"<ValueBet {self.selection} @{self.market_odds} edge={self.edge:+.3f}>"


def edge(model_prob: float, decimal_odds: float) -> float:
    """Expected value per unit staked minus 1: ``model_prob * odds - 1``."""
    return model_prob * decimal_odds - 1.0


def implied_probs(odds: Odds) -> tuple[float, float, float]:
    """Overround-normalized market probabilities from 1X2 decimal odds."""
    raw = [1.0 / o for o in odds]
    total = sum(raw)
    return (raw[0] / total, raw[1] / total, raw[2] / total)


def find_value_bet(probs: MatchProbs, odds: Odds, threshold: float) -> ValueBet | None:
    """Return the highest-edge selection clearing ``threshold``, or None.

    Args:
        probs: Model 1X2 probabilities.
        odds: Decimal odds in (HOME, DRAW, AWAY) order.
        threshold: Minimum edge to bet (e.g. 0.05 = require 5% expected value).
    """
    candidates = [
        ValueBet(sel, p, o, edge(p, o))
        for sel, p, o in zip(RESULT_CLASSES, probs.as_tuple(), odds, strict=True)
    ]
    best = max(candidates, key=lambda c: c.edge)
    return best if best.edge >= threshold else None
