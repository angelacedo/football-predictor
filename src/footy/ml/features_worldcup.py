"""Feature engineering for World Cup 1X2 prediction.

Deliberately NOT footy.ml.features's rolling-window design - that pattern
assumes weekly club football, where recent form carries real signal. World
Cup matches are 4 years apart with largely different squads under the same
team name, so a rolling "recent form" window would blend unrelated eras
together and a rest-days feature would compute ~1,460+ days for every
team's first match of a new tournament. Instead: a per-match static lookup -
each team's FIFA ranking as of a fixed pre-tournament snapshot date (never
live, never updates mid-tournament, leakage-safe by construction since the
snapshot always predates kickoff), plus a static host-nation flag.

Also plus a static is_knockout flag: real bug found live 2026-07-14 - a
knockout match tied after extra time and decided by penalties (e.g. the real
2022 final, Argentina beat France) has goals.home == goals.away, which
result_from_goals would mislabel DRAW. A knockout match always has a real
winner, so training labels use the provider's own winner_home/winner_away
flags (true/false once decided, including by penalties; null/null only for
a genuine drawn group-stage game) instead of comparing goals directly.
is_knockout also lets scripts/predict_upcoming.py hard-zero the draw
probability it shows for knockout fixtures - a classifier fit on both
group (draws real) and knockout (draws impossible) rows can still assign
some residual draw probability to a knockout row's features, so the label
fix alone doesn't guarantee 0% shown; the serving-side renormalization does.

Ranking data: data/fifa_rankings_snapshot.csv, vendored from
github.com/Dato-Futbol/fifa-ranking (community-maintained; verified live
2026-07-06 against all 65 real WC-participating teams across 2010-2026,
zero unmatched names after resolving 7 real API-Football/CSV naming
differences - see scripts/train_world_cup.py). That source repo's last
commit was Oct 2024, so the 2026 tournament's snapshot is frozen at
2024-09-19 - a known, accepted staleness (no live FIFA ranking API exists;
FIFA's own internal endpoint was confirmed dead 2026-07-06: /v3 returns a
formal 404, /v1 hits an Akamai bot-block).

Path resolution is deliberately cwd-relative, NOT __file__-based: this
module lives under src/footy/ml/ which setuptools pip-installs into
site-packages, so __file__ would resolve inside site-packages after
`pip install .` (non-editable), not back to this repo's data/ directory -
the exact class of bug that crash-looped production once already this
project (see joblog packaging incident). Every caller (scripts/, always run
as `python scripts/x.py` from the repo root / Docker WORKDIR) sees cwd ==
repo root, matching every other relative path already used that way in this
codebase (e.g. scripts/init_db.py's schema.sql, though that one resolves via
__file__ safely since scripts/ itself is never pip-installed).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from footy.domain import result_from_goals

FEATURE_COLUMNS_WORLDCUP: tuple[str, ...] = (
    "fifa_rank_home",
    "fifa_rank_away",
    "is_host_home",
    "is_host_away",
    "is_knockout",
)

# Group-stage rounds are named "Group Stage - N" by API-Football; everything
# else (Round of 16, Quarter-finals, ...) is knockout - a real winner is
# always decided (via ET/penalties if needed), a draw is structurally
# impossible. Missing round (older rows not yet re-synced) defaults to 0.0 -
# never force a match into the knockout bucket without real round data.
_GROUP_STAGE_MARKER = "Group"

DEFAULT_RANKINGS_PATH = Path("data/fifa_rankings_snapshot.csv")
# ponytail: one worse than the worst real WC-participant rank seen (105) by
# a wide margin - FIFA ranks ~210 national teams total, so an unranked/
# unmatched team should score clearly below every real participant, not
# tie with the actual worst-ranked one.
_UNRANKED_DEFAULT = 211.0

_HOST_NATIONS: dict[int, frozenset[str]] = {
    2010: frozenset({"South Africa"}),
    2014: frozenset({"Brazil"}),
    2018: frozenset({"Russia"}),
    2022: frozenset({"Qatar"}),
    2026: frozenset({"United States", "Canada", "Mexico"}),
}


def load_rankings(path: Path | str | None = None) -> pd.DataFrame:
    """Load the vendored ranking snapshot: columns season, team, fifa_rank."""
    return pd.read_csv(path or DEFAULT_RANKINGS_PATH)


def compute_feature_frame_worldcup(df: pd.DataFrame, rankings: pd.DataFrame) -> pd.DataFrame:
    """Per-match static lookup, not a rolling sweep - see module docstring.

    Args:
        df: Matches with columns ``id, season, home_team, away_team,
            home_goals, away_goals, round, winner_home, winner_away``
            (season = tournament year, e.g. 2026 - same shape
            footy.data.matches_dataframe already returns).
        rankings: Output of :func:`load_rankings`.

    Returns:
        DataFrame indexed by match ``id`` with :data:`FEATURE_COLUMNS_WORLDCUP`
        plus a ``result`` column (1X2 label, or None for unplayed matches).
    """
    rank_lookup: dict[tuple[int, str], float] = {
        (int(rec["season"]), str(rec["team"])): float(rec["fifa_rank"])
        for rec in rankings.to_dict("records")
        if pd.notna(rec["fifa_rank"])
    }

    rows: list[dict[str, object]] = []
    for rec in df.to_dict("records"):
        season = int(rec["season"])
        home, away = rec["home_team"], rec["away_team"]
        hosts = _HOST_NATIONS.get(season, frozenset())
        result = None
        if pd.notna(rec.get("home_goals")) and pd.notna(rec.get("away_goals")):
            winner_home = rec.get("winner_home")
            winner_away = rec.get("winner_away")
            if pd.notna(winner_home) and bool(winner_home):
                result = "HOME"
            elif pd.notna(winner_away) and bool(winner_away):
                result = "AWAY"
            else:
                # Real draw, or older row missing winner_home/winner_away
                # (not yet re-synced) - goal comparison is the correct
                # fallback either way.
                result = result_from_goals(int(rec["home_goals"]), int(rec["away_goals"]))
        round_val = rec.get("round")
        is_knockout = (
            1.0
            if (pd.notna(round_val) and _GROUP_STAGE_MARKER not in str(round_val))
            else 0.0
        )
        rows.append(
            {
                "id": rec["id"],
                "fifa_rank_home": rank_lookup.get((season, home), _UNRANKED_DEFAULT),
                "fifa_rank_away": rank_lookup.get((season, away), _UNRANKED_DEFAULT),
                "is_host_home": 1.0 if home in hosts else 0.0,
                "is_host_away": 1.0 if away in hosts else 0.0,
                "is_knockout": is_knockout,
                "result": result,
            }
        )
    return pd.DataFrame(rows).set_index("id")
