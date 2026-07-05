"""Fetch 1X2 odds for scheduled matches using the configured provider chain.

Usage:
    python scripts/fetch_odds.py            # pre-match odds
    python scripts/fetch_odds.py --closing  # tag as closing odds

Provider selection is via ODDS_PROVIDER_PRIMARY/ODDS_PROVIDER_FALLBACK in
.env — see README "Providers". Unchanged default (only FOOTBALL_API_KEY set)
behaves exactly as before this feature.
"""

from __future__ import annotations

import logging
import sys
import time

from sqlalchemy import select

from footy.db import session_scope
from footy.ingest.odds import fetch_odds
from footy.orm import Match

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.fetch_odds")

# ponytail: fixed delay, not a real rate limiter - swap for one if a provider's
# actual per-minute quota needs tighter/looser pacing than this.
REQUEST_DELAY_SECONDS = 0.5


def main() -> None:
    is_closing = "--closing" in sys.argv[1:]
    with session_scope() as session:
        fixtures = session.scalars(
            select(Match.api_fixture_id).where(Match.status == "SCHEDULED")
        ).all()

    failed = 0
    for api_fixture_id in fixtures:
        try:
            fetch_odds(api_fixture_id, is_closing=is_closing)
        except Exception:
            failed += 1
            log.exception("Odds fetch failed for fixture %d, skipping", api_fixture_id)
        time.sleep(REQUEST_DELAY_SECONDS)

    if failed:
        log.warning("%d/%d fixture(s) failed", failed, len(fixtures))


if __name__ == "__main__":
    main()
