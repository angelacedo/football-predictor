"""Fetch 1X2 (Match Winner) odds from API-Football and store them.

Example:
    >>> parse_match_winner(bookmaker_obj)   # doctest: +SKIP
    (2.1, 3.4, 3.5)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from footy.db import session_scope
from footy.ingest.client import ApiFootball
from footy.orm import Match, Odds

log = logging.getLogger("footy.ingest.odds")

MATCH_WINNER = "Match Winner"
_SIDE = {"Home": 0, "Draw": 1, "Away": 2}


def parse_match_winner(bookmaker: dict[str, Any]) -> tuple[float, float, float] | None:
    """Extract (home, draw, away) decimal odds from a bookmaker object, or None."""
    for bet in bookmaker.get("bets", []):
        if bet.get("name") != MATCH_WINNER:
            continue
        odds: list[float | None] = [None, None, None]
        for value in bet.get("values", []):
            idx = _SIDE.get(value.get("value"))
            if idx is not None:
                odds[idx] = float(value["odd"])
        if all(o is not None for o in odds):
            return (odds[0], odds[1], odds[2])  # type: ignore[return-value]
    return None


def _dec3(value: float) -> Decimal:
    return Decimal(str(round(value, 3)))


def fetch_odds(api_fixture_id: int, client: ApiFootball | None = None,
               is_closing: bool = False) -> int:
    """Fetch and store all Match-Winner odds for a fixture.

    Returns:
        Number of odds rows written. 0 if the fixture is unknown locally.
    """
    api = client or ApiFootball()
    written = 0
    with session_scope() as session:
        match = session.scalar(
            select(Match).where(Match.api_fixture_id == api_fixture_id)
        )
        if match is None:
            log.warning("Fixture %d not in DB — run match sync first", api_fixture_id)
            return 0
        items = api.get("odds", {"fixture": api_fixture_id})
        for item in items:
            for bookmaker in item.get("bookmakers", []):
                parsed = parse_match_winner(bookmaker)
                if parsed is None:
                    continue
                session.add(
                    Odds(
                        match_id=match.id,
                        bookmaker=bookmaker.get("name", "unknown"),
                        odds_home=_dec3(parsed[0]),
                        odds_draw=_dec3(parsed[1]),
                        odds_away=_dec3(parsed[2]),
                        is_closing=is_closing,
                    )
                )
                written += 1
    log.info("Stored %d odds row(s) for fixture %d", written, api_fixture_id)
    return written
