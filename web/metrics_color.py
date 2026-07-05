"""Green->red color scale for scannable Brier/log-loss table cells.

Thresholds match README's "Interpreting the numbers" section: Brier 0=perfect,
~0.67=uniform 1/3 guess; log loss 0=perfect, ln(3)~=1.10=uniform guess.
"""

from __future__ import annotations

_GOOD = (0x16, 0xA3, 0x4A)  # --good
_BAD = (0xDC, 0x26, 0x26)  # --bad


def _interp(value: float, good: float, bad: float) -> str:
    t = max(0.0, min(1.0, (value - good) / (bad - good)))
    r = round(_GOOD[0] + (_BAD[0] - _GOOD[0]) * t)
    g = round(_GOOD[1] + (_BAD[1] - _GOOD[1]) * t)
    bl = round(_GOOD[2] + (_BAD[2] - _GOOD[2]) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


def brier_color(value: float) -> str:
    return _interp(value, good=0.15, bad=0.67)


def log_loss_color(value: float) -> str:
    return _interp(value, good=0.4, bad=1.10)
