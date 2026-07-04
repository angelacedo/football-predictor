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

from sqlalchemy import select

from footy.db import session_scope
from footy.ingest.odds import fetch_odds
from footy.orm import Match

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    is_closing = "--closing" in sys.argv[1:]
    with session_scope() as session:
        fixtures = session.scalars(
            select(Match.api_fixture_id).where(Match.status == "SCHEDULED")
        ).all()

    for api_fixture_id in fixtures:
        fetch_odds(api_fixture_id, is_closing=is_closing)


if __name__ == "__main__":
    main()
