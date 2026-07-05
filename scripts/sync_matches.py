"""Sync fixtures/results for a league/season into ``matches``.

Usage:
    python scripts/sync_matches.py <league_id> <season>
"""

from __future__ import annotations

import logging
import sys

from footy.ingest.matches import sync_league

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)
    sync_league(int(sys.argv[1]), int(sys.argv[2]))


if __name__ == "__main__":
    main()
