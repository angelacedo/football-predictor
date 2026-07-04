"""Stake sizing: flat and fractional Kelly."""

from __future__ import annotations

import pytest

from footy.betting.staking import flat_stake, kelly_fraction, kelly_stake


def test_flat_stake() -> None:
    assert flat_stake(1000, 0.01) == pytest.approx(10.0)


def test_kelly_positive_edge() -> None:
    # p=0.6, odds=2.0 -> b=1, f* = (1*0.6 - 0.4)/1 = 0.2; quarter Kelly = 0.05
    assert kelly_fraction(0.6, 2.0, fraction=0.25) == pytest.approx(0.05)
    assert kelly_stake(1000, 0.6, 2.0, fraction=0.25) == pytest.approx(50.0)


def test_kelly_negative_edge_is_zero() -> None:
    assert kelly_fraction(0.4, 2.0, fraction=0.25) == 0.0
    assert kelly_stake(1000, 0.4, 2.0) == 0.0


def test_kelly_bad_odds_is_zero() -> None:
    assert kelly_fraction(0.9, 1.0, fraction=0.25) == 0.0
