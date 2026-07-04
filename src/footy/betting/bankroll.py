"""Bankroll and risk limits for paper betting.

Caps a desired stake by (a) a per-bet maximum and (b) remaining open exposure for
a group (e.g. a league or market), so a single group can't soak the whole roll.
Balance only moves on settlement — this is paper accounting, not real funds.

Example:
    >>> br = Bankroll(1000.0, max_stake_frac=0.05, max_group_exposure_frac=0.10)
    >>> br.allowed_stake(200.0, group="EPL")   # capped to 5% per-bet
    50.0
    >>> _ = br.place(50.0, group="EPL")
    >>> br.allowed_stake(200.0, group="EPL")   # 10% group cap, 50 already open
    50.0
    >>> br.settle(stake=50.0, pnl=50.0, group="EPL")
    >>> br.balance
    1050.0
"""

from __future__ import annotations

from collections import defaultdict


class Bankroll:
    """Stateful paper bankroll with per-bet and per-group exposure caps."""

    def __init__(
        self,
        balance: float,
        max_stake_frac: float = 0.05,
        max_group_exposure_frac: float = 0.10,
    ) -> None:
        self.balance = balance
        self.max_stake_frac = max_stake_frac
        self.max_group_exposure_frac = max_group_exposure_frac
        self._open: dict[str, float] = defaultdict(float)

    def allowed_stake(self, desired: float, group: str) -> float:
        """Return ``desired`` clamped by per-bet and remaining group-exposure caps."""
        per_bet_cap = self.balance * self.max_stake_frac
        group_room = self.balance * self.max_group_exposure_frac - self._open[group]
        return max(0.0, min(desired, per_bet_cap, group_room))

    def place(self, stake: float, group: str) -> float:
        """Reserve ``stake`` of open exposure for ``group``; returns the stake."""
        self._open[group] += stake
        return stake

    def settle(self, stake: float, pnl: float, group: str) -> None:
        """Apply a settled bet: credit pnl and release the reserved exposure."""
        self.balance += pnl
        self._open[group] = max(0.0, self._open[group] - stake)

    def __repr__(self) -> str:
        return f"<Bankroll balance={self.balance:.2f} open={dict(self._open)}>"
