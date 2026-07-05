"""Monogram badge helpers - no images, no network, no broken-image state possible.

Football has no verified free crest-image source (checked TheSportsDB's free
tier live: team search resolves, but strTeamBadge/strTeamLogo are null - image
assets are gated behind their paid tier). Every badge here is server-computed
text-on-color, not an <img>, so there is nothing to 404.
"""

from __future__ import annotations

import hashlib

_STOPWORDS = {"fc", "cf", "the", "de", "of"}


def initials(name: str) -> str:
    """1-2 letter initials from a team/driver/constructor name.

    Multi-word ("Manchester United" -> "MU"): first letter of the first two
    significant words (short connector words like "FC"/"de" skipped).
    Single-word ("Chelsea" -> "CH"): first two letters.
    """
    words = [w for w in name.split() if w.lower() not in _STOPWORDS]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    if words:
        return words[0][:2].upper()
    return "?"


def color_for(name: str) -> str:
    """Deterministic hex color from a hash of ``name`` - same team always gets
    the same color, no lookup, no manual mapping table to maintain."""
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    hue = int(digest[:4], 16) % 360
    return _hsl_to_hex(hue, 55, 45)


def readable_text_color(bg_hex: str) -> str:
    """'#000000' or '#ffffff', whichever contrasts better against bg_hex.

    YIQ brightness heuristic (not full WCAG contrast math) - good enough for
    a dashboard badge, simple to reason about. Handles arbitrary real hex
    values (F1's OpenF1 team_colour) as well as our own hash-derived ones,
    across the whole lightness range - this is what guarantees a light bg
    always gets black text and a dark bg always gets white text, rather than
    relying on luck from a fixed lightness choice.
    """
    r, g, b = _hex_to_rgb(bg_hex)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "#000000" if brightness > 128 else "#ffffff"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hsl_to_hex(h: int, s: int, ell: int) -> str:
    s_frac = s / 100
    ell_frac = ell / 100
    c = (1 - abs(2 * ell_frac - 1)) * s_frac
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = ell_frac - c / 2
    r, g, b = {
        0: (c, x, 0.0), 1: (x, c, 0.0), 2: (0.0, c, x),
        3: (0.0, x, c), 4: (x, 0.0, c), 5: (c, 0.0, x),
    }[h // 60]
    return f"#{round((r + m) * 255):02x}{round((g + m) * 255):02x}{round((b + m) * 255):02x}"
