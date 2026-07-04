"""Scoring math and aggregate performance metrics.

Per-prediction scores (:func:`brier_score`, :func:`log_loss_single`) are the pure
functions the validator stores on each row; the aggregate helpers summarize a set
of already-validated predictions.

Probability order is always ``(HOME, DRAW, AWAY)`` — see
:data:`footy.ml.features.RESULT_CLASSES`.

Example:
    >>> brier_score((0.7, 0.2, 0.1), "HOME")
    0.14000000000000004
    >>> round(log_loss_single((0.7, 0.2, 0.1), "HOME"), 4)
    0.3567
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import pandas as pd
from sklearn.calibration import calibration_curve

from footy.ml.features import RESULT_CLASSES

Probs = Sequence[float]
_EPS = 1e-15


def _onehot(actual: str) -> tuple[int, int, int]:
    if actual not in RESULT_CLASSES:
        raise ValueError(f"Unknown result {actual!r}; expected one of {RESULT_CLASSES}")
    return tuple(1 if c == actual else 0 for c in RESULT_CLASSES)  # type: ignore[return-value]


def brier_score(probs: Probs, actual: str) -> float:
    """Multiclass Brier score: ``sum((p_i - y_i)**2)`` over HOME/DRAW/AWAY.

    Range 0 (perfect) .. 2 (worst). ``~0.667`` is a uniform 1/3 guess.
    """
    y = _onehot(actual)
    return sum((p - t) ** 2 for p, t in zip(probs, y, strict=True))


def log_loss_single(probs: Probs, actual: str, eps: float = _EPS) -> float:
    """Log loss for one prediction: ``-log(clip(p_actual))``.

    With a one-hot target this reduces to the negative log of the probability
    assigned to the true outcome. ``p`` is clipped to ``[eps, 1-eps]`` so ``p=0``
    or ``p=1`` never blows up to infinity.
    """
    idx = RESULT_CLASSES.index(actual) if actual in RESULT_CLASSES else _raise(actual)
    p = min(max(probs[idx], eps), 1.0 - eps)
    return -math.log(p)


def _raise(actual: str) -> int:  # pragma: no cover - tiny guard helper
    raise ValueError(f"Unknown result {actual!r}; expected one of {RESULT_CLASSES}")


def predicted_result(probs: Probs) -> str:
    """Return the argmax 1X2 label for a probability vector."""
    return RESULT_CLASSES[max(range(len(RESULT_CLASSES)), key=lambda i: probs[i])]


# --- Aggregate metrics over a set of validated predictions -------------------
# Expected DataFrame columns: prob_home_win, prob_draw, prob_away_win,
# actual_result, is_correct, brier_score, log_loss, and optionally league.


def overall_accuracy(df: pd.DataFrame) -> float:
    """Fraction of predictions whose argmax matched the actual result."""
    return float(df["is_correct"].mean()) if len(df) else float("nan")


def mean_brier(df: pd.DataFrame) -> float:
    """Mean stored Brier score (lower is better)."""
    return float(df["brier_score"].mean()) if len(df) else float("nan")


def mean_log_loss(df: pd.DataFrame) -> float:
    """Mean stored log loss (lower is better; uniform guess ~= ln(3) ~= 1.10)."""
    return float(df["log_loss"].mean()) if len(df) else float("nan")


def summary(df: pd.DataFrame) -> dict[str, float]:
    """Return the headline metrics as a dict."""
    return {
        "n": float(len(df)),
        "accuracy": overall_accuracy(df),
        "brier": mean_brier(df),
        "log_loss": mean_log_loss(df),
    }


def breakdown_by(df: pd.DataFrame, column: str) -> dict[str, dict[str, float]]:
    """Return :func:`summary` metrics grouped by ``column`` (e.g. 'league')."""
    return {str(key): summary(group) for key, group in df.groupby(column)}


def calibration_by_class(
    df: pd.DataFrame, n_bins: int = 10
) -> Mapping[str, tuple[list[float], list[float]]]:
    """Reliability curve per class: maps class -> (predicted_prob, observed_freq).

    Uses :func:`sklearn.calibration.calibration_curve`. A well-calibrated model
    hugs the diagonal (predicted 0.6 => wins ~60% of the time).
    """
    prob_cols = {"HOME": "prob_home_win", "DRAW": "prob_draw", "AWAY": "prob_away_win"}
    out: dict[str, tuple[list[float], list[float]]] = {}
    for cls, col in prob_cols.items():
        y_true = (df["actual_result"] == cls).astype(int)
        if y_true.nunique() < 2:
            continue  # calibration_curve needs both outcomes present
        frac_pos, mean_pred = calibration_curve(y_true, df[col], n_bins=n_bins)
        out[cls] = (list(mean_pred), list(frac_pos))
    return out
