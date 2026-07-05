"""One-off backfill: deepen circuit_history_pos with pre-OpenF1 F1 history via Jolpica.

Scoped to 2014+ only - before 2014 F1 car numbers weren't permanent, so
merging older rows into F1Entry.driver_number risks conflating two drivers'
histories (see jolpica.py's docstring). Not a scheduled job - run manually,
rarely. Batches by season (one schedule call + one results call per round),
per Jolpica's own rate-limit guidance (4 req/s burst, 500 req/hour) - a small
per-round delay keeps this well under both.

Usage:
    python scripts/backfill_f1_historical.py <season_start> <season_end>
"""

from __future__ import annotations

import logging
import sys
import time

from sports.f1.ingest.providers.jolpica import JolpicaProvider
from sports.f1.ingest.sessions import sync_season

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("backfill_f1_historical")

MIN_SEASON = 2014
SEASON_DELAY_SECONDS = 1.0


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)
    season_start, season_end = int(sys.argv[1]), int(sys.argv[2])
    if season_start < MIN_SEASON:
        raise SystemExit(
            f"season_start must be >= {MIN_SEASON} (pre-2014 car numbers aren't "
            "permanent - see jolpica.py's docstring). Not supported by this script."
        )

    provider = JolpicaProvider()
    for season in range(season_start, season_end + 1):
        written = sync_season(season, session_type="RACE", provider=provider)
        log.info("Backfilled %d RACE session(s) for %d", written, season)
        time.sleep(SEASON_DELAY_SECONDS)


if __name__ == "__main__":
    main()
