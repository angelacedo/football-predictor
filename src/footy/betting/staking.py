"""Stake sizing. Paper only — computes amounts, never moves money.

Two methods:

* **flat** — a fixed fraction of bankroll per bet. Boring, robust, hard to blow up.
* **fractional Kelly** — the growth-optimal Kelly fraction scaled down (default 1/4).
  Full Kelly maximizes long-run growth but is brutally volatile and unforgiving of
  probability-estimate error, so practitioners bet a fraction of it.

Example:
    >>> flat_stake(1000, 0.01)
    10.0
    >>> round(kelly_stake(1000, prob=0.6, odds=2.0, fraction=0.25), 2)
    50.0
    >>> kelly_stake(1000, prob=0.4, odds=2.0, fraction=0.25)  # negative edge -> no bet
    0.0
"""

from __future__ import annotations


def flat_stake(bankroll: float, unit_fraction: float = 0.01) -> float:
    """Fixed fraction of bankroll (default 1%)."""
    return bankroll * unit_fraction


def kelly_fraction(prob: float, odds: float, fraction: float = 0.25) -> float:
    """Fractional-Kelly bankroll fraction for a bet.

    ``f* = (b*p - q) / b`` with ``b = odds - 1`` and ``q = 1 - p``, scaled by
    ``fraction``. Non-positive edge clamps to 0 (no bet).
    """
    b = odds - 1.0
    if b <= 0:
        return 0.0
    q = 1.0 - prob
    f = (b * prob - q) / b
    return max(0.0, f) * fraction


def kelly_stake(bankroll: float, prob: float, odds: float, fraction: float = 0.25) -> float:
    """Stake amount from fractional Kelly on ``bankroll``."""
    return bankroll * kelly_fraction(prob, odds, fraction)
