"""Replay settled paper bets into performance stats.

Answers "do I actually have an edge?" — ROI, hit-rate, worst drawdown, and CLV
(closing-line value: did we take better-than-closing odds, the strongest signal
that an edge is real rather than variance).

Example:
    >>> bets = [SettledBet("HOME", odds=2.0, stake=1.0, won=True),
    ...         SettledBet("AWAY", odds=3.0, stake=1.0, won=False)]
    >>> r = backtest(bets)
    >>> r.total_pnl, r.roi
    (0.0, 0.0)
    >>> backtest([SettledBet("HOME", 2.0, 1.0, won=True)]).roi
    1.0
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class SettledBet:
    """A resolved paper bet. ``closing_odds`` optional, enables CLV."""

    selection: str
    odds: float
    stake: float
    won: bool
    closing_odds: float | None = None

    @property
    def pnl(self) -> float:
        """Profit/loss: ``stake*(odds-1)`` on a win, ``-stake`` on a loss."""
        return self.stake * (self.odds - 1.0) if self.won else -self.stake


@dataclass(frozen=True)
class BacktestReport:
    """Aggregate paper-betting performance."""

    n: int
    total_staked: float
    total_pnl: float
    roi: float
    hit_rate: float
    max_drawdown: float
    clv: float | None

    def __repr__(self) -> str:
        clv = f"{self.clv:+.3f}" if self.clv is not None else "n/a"
        return (
            f"<BacktestReport n={self.n} roi={self.roi:+.4f} "
            f"hit={self.hit_rate:.3f} maxDD={self.max_drawdown:.2f} clv={clv}>"
        )


def backtest(bets: Sequence[SettledBet]) -> BacktestReport:
    """Compute ROI, hit-rate, max drawdown and CLV over ``bets``."""
    if not bets:
        return BacktestReport(0, 0.0, 0.0, float("nan"), float("nan"), 0.0, None)

    total_staked = sum(b.stake for b in bets)
    total_pnl = sum(b.pnl for b in bets)
    wins = sum(1 for b in bets if b.won)

    # Max drawdown over the cumulative-pnl equity curve.
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for b in bets:
        cum += b.pnl
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)

    clv_samples = [b.odds / b.closing_odds - 1.0 for b in bets if b.closing_odds]
    clv = sum(clv_samples) / len(clv_samples) if clv_samples else None

    return BacktestReport(
        n=len(bets),
        total_staked=total_staked,
        total_pnl=total_pnl,
        roi=total_pnl / total_staked if total_staked else float("nan"),
        hit_rate=wins / len(bets),
        max_drawdown=max_dd,
        clv=clv,
    )
