"""Fetch 1X2 odds and store them, provider-agnostic with primary/fallback.

Consumes :class:`footy.ingest.schemas.OddsDTO` only — no provider-specific JSON
here. If ``provider`` isn't passed explicitly, the primary provider
(``ODDS_PROVIDER_PRIMARY``) is tried first; if it raises or returns no odds,
the fallback (``ODDS_PROVIDER_FALLBACK``, if set) is tried next.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select

from footy.config import get_settings
from footy.db import session_scope
from footy.ingest.providers.base import Provider, ProviderError
from footy.ingest.providers.registry import build_provider
from footy.ingest.schemas import OddsDTO, OddsQuery
from footy.orm import Match, Odds

log = logging.getLogger("footy.ingest.odds")


def _dec3(value: float) -> Decimal:
    return Decimal(str(round(value, 3)))


def _fetch_with_fallback(query: OddsQuery) -> list[OddsDTO]:
    """Try the configured primary odds provider, then the fallback, if any."""
    settings = get_settings()
    settings.require_odds_provider()
    chain = [settings.odds_provider_primary]
    if settings.odds_provider_fallback:
        chain.append(settings.odds_provider_fallback)

    for i, name in enumerate(chain):
        has_next = i + 1 < len(chain)
        try:
            odds = build_provider(name).get_odds(query)
        except ProviderError as exc:
            log.warning("Odds provider '%s' failed (%s)%s", name, exc,
                        " — trying fallback" if has_next else "")
            continue
        if odds:
            if i > 0:
                log.info("Odds provider '%s' (fallback) returned odds", name)
            return odds
        log.warning("Odds provider '%s' returned no odds%s", name,
                    " — trying fallback" if has_next else "")
    return []


def fetch_odds(api_fixture_id: int, provider: Provider | None = None,
                is_closing: bool = False) -> int:
    """Fetch and store all 1X2 odds for a fixture.

    Args:
        api_fixture_id: The fixtures-provider's id for this match (as stored
            in ``matches.api_fixture_id``).
        provider: Use this exact provider only (no fallback chain). Defaults
            to the configured primary/fallback chain when None.
        is_closing: Force every stored row's ``is_closing`` flag to True
            (e.g. for a manual closing-line snapshot); a provider that already
            marks its own odds as closing sets it regardless.

    Returns:
        Number of odds rows written. 0 if the fixture is unknown locally or
        no provider returned odds.
    """
    written = 0
    with session_scope() as session:
        match = session.scalar(
            select(Match).where(Match.api_fixture_id == api_fixture_id)
        )
        if match is None:
            log.warning("Fixture %d not in DB — run match sync first", api_fixture_id)
            return 0

        query = OddsQuery(
            external_fixture_id=api_fixture_id,
            home_team=match.home_team,
            away_team=match.away_team,
            kickoff=match.kickoff,
        )
        odds = provider.get_odds(query) if provider is not None else _fetch_with_fallback(query)

        for dto in odds:
            session.add(
                Odds(
                    match_id=match.id,
                    bookmaker=dto.bookmaker,
                    odds_home=_dec3(dto.odds_home),
                    odds_draw=_dec3(dto.odds_draw),
                    odds_away=_dec3(dto.odds_away),
                    is_closing=dto.is_closing or is_closing,
                )
            )
            written += 1
    log.info("Stored %d odds row(s) for fixture %d", written, api_fixture_id)
    return written
