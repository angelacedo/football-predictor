"""Backtest ROI, hit-rate, drawdown, CLV."""

from __future__ import annotations

import math

import pytest

from footy.betting.backtest import SettledBet, backtest


def test_single_winner_roi() -> None:
    r = backtest([SettledBet("HOME", odds=2.0, stake=1.0, won=True)])
    assert r.total_pnl == pytest.approx(1.0)
    assert r.roi == pytest.approx(1.0)
    assert r.hit_rate == pytest.approx(1.0)


def test_win_then_loss_breaks_even() -> None:
    bets = [
        SettledBet("HOME", odds=2.0, stake=1.0, won=True),
        SettledBet("AWAY", odds=3.0, stake=1.0, won=False),
    ]
    r = backtest(bets)
    assert r.total_pnl == pytest.approx(0.0)
    assert r.roi == pytest.approx(0.0)
    assert r.hit_rate == pytest.approx(0.5)


def test_max_drawdown() -> None:
    # +1 then -1 -> peak 1, trough 0 -> drawdown 1.
    bets = [
        SettledBet("HOME", odds=2.0, stake=1.0, won=True),
        SettledBet("AWAY", odds=3.0, stake=1.0, won=False),
    ]
    assert backtest(bets).max_drawdown == pytest.approx(1.0)


def test_clv() -> None:
    # took 2.2, closed 2.0 -> beat close by 10%.
    r = backtest([SettledBet("HOME", odds=2.2, stake=1.0, won=True, closing_odds=2.0)])
    assert r.clv == pytest.approx(0.1)


def test_empty() -> None:
    r = backtest([])
    assert r.n == 0
    assert math.isnan(r.roi)
