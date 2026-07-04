"""Scoring math used by PredictionValidator (Brier, log loss, argmax)."""

from __future__ import annotations

import math

import pytest

from footy.predictions.metrics import brier_score, log_loss_single, predicted_result


def test_brier_known_case() -> None:
    # (0.7-1)^2 + 0.2^2 + 0.1^2 = 0.09 + 0.04 + 0.01
    assert brier_score((0.7, 0.2, 0.1), "HOME") == pytest.approx(0.14)


def test_brier_perfect_and_worst() -> None:
    assert brier_score((1.0, 0.0, 0.0), "HOME") == pytest.approx(0.0)
    assert brier_score((1.0, 0.0, 0.0), "AWAY") == pytest.approx(2.0)


def test_log_loss_known_case() -> None:
    assert log_loss_single((0.7, 0.2, 0.1), "HOME") == pytest.approx(-math.log(0.7))


def test_log_loss_clips_zero_probability() -> None:
    # True outcome got probability 0 — must be finite, not inf.
    loss = log_loss_single((1.0, 0.0, 0.0), "AWAY")
    assert math.isfinite(loss)
    assert loss == pytest.approx(-math.log(1e-15))


def test_log_loss_clips_one_probability() -> None:
    assert math.isfinite(log_loss_single((1.0, 0.0, 0.0), "HOME"))


def test_predicted_result_argmax() -> None:
    assert predicted_result((0.6, 0.25, 0.15)) == "HOME"
    assert predicted_result((0.2, 0.5, 0.3)) == "DRAW"
    assert predicted_result((0.1, 0.2, 0.7)) == "AWAY"


def test_unknown_result_raises() -> None:
    with pytest.raises(ValueError):
        brier_score((0.5, 0.3, 0.2), "TIE")
