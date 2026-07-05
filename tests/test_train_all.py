"""CLI exit-code contract for scripts/train_all.py - no DB/network, no real workers."""

from __future__ import annotations

import sys

import pytest

import train_all


def test_main_returns_nonzero_if_any_result_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        train_all,
        "train_all_parallel",
        lambda leagues, algorithms, workers: {
            "baseline_La_Liga": "models/baseline_La_Liga_20260101T000000Z.pkl",
            "xgboost_La_Liga": "ERROR: No finished matches to train on.",
        },
    )
    monkeypatch.setattr(sys, "argv", ["train_all.py", "--leagues", "La Liga"])

    assert train_all.main() == 1


def test_main_returns_zero_if_all_succeed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        train_all,
        "train_all_parallel",
        lambda leagues, algorithms, workers: {
            "baseline_La_Liga": "models/baseline_La_Liga_20260101T000000Z.pkl",
        },
    )
    monkeypatch.setattr(sys, "argv", ["train_all.py", "--leagues", "La Liga"])

    assert train_all.main() == 0


def test_main_prints_every_result_even_on_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        train_all,
        "train_all_parallel",
        lambda leagues, algorithms, workers: {
            "baseline_La_Liga": "models/baseline_La_Liga_latest.pkl",
            "xgboost_La_Liga": "ERROR: boom",
        },
    )
    monkeypatch.setattr(sys, "argv", ["train_all.py", "--leagues", "La Liga"])

    train_all.main()

    out = capsys.readouterr().out
    assert "baseline_La_Liga" in out
    assert "xgboost_La_Liga" in out
    assert "ERROR: boom" in out
