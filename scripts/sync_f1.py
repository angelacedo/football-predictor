"""Sync F1 sessions/entries for a season.

Usage:
    python scripts/sync_f1.py <season> [session_type]
    python scripts/sync_f1.py 2024
    python scripts/sync_f1.py 2024 QUALIFYING
"""

from __future__ import annotations

import logging
import sys

from sports.f1.ingest.sessions import sync_season

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        raise SystemExit(1)
    season = int(sys.argv[1])
    session_type = sys.argv[2] if len(sys.argv) == 3 else "RACE"
    sync_season(season, session_type=session_type)


if __name__ == "__main__":
    main()
