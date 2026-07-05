"""Value detection: edge signs and selection."""

from __future__ import annotations

import pytest

from footy.betting.value import edge, find_value_bet, implied_probs
from footy.domain import MatchProbs


def test_edge_sign() -> None:
    assert edge(0.6, 2.0) == pytest.approx(0.2)   # +EV
    assert edge(0.4, 2.0) == pytest.approx(-0.2)  # -EV


def test_find_value_bet_selects_home() -> None:
    bet = find_value_bet(MatchProbs(0.6, 0.25, 0.15), (2.0, 3.5, 5.0), threshold=0.05)
    assert bet is not None
    assert bet.selection == "HOME"
    assert bet.edge == pytest.approx(0.2)


def test_find_value_bet_none_below_threshold() -> None:
    # All edges negative: home 0.4*2-1=-0.2, draw 0.3*3-1=-0.1, away 0.3*3-1=-0.1.
    assert find_value_bet(MatchProbs(0.4, 0.3, 0.3), (2.0, 3.0, 3.0), threshold=0.05) is None


def test_implied_probs_sum_to_one() -> None:
    p = implied_probs((2.0, 3.5, 5.0))
    assert sum(p) == pytest.approx(1.0)
