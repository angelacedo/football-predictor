"""Fetch and persist advanced stats (xG, possession) onto ``matches``.

Separate from ``matches.py``/``odds.py`` so their existing contracts (return
ints, same DB writes) don't grow a third concern. Stats are optional: if
``STATS_PROVIDER`` is unset, :func:`fetch_stats` is a no-op — matches persist
with xG/possession left NULL, exactly as before this feature existed.

Note: not consumed by ``ml/features.py`` yet — this module only persists the
values for later use.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select

from footy.config import get_settings
from footy.db import session_scope
from footy.ingest.providers.base import Provider
from footy.ingest.providers.registry import build_provider
from footy.orm import Match

log = logging.getLogger("footy.ingest.stats")


def _dec2(value: float | None) -> Decimal | None:
    return Decimal(str(round(value, 2))) if value is not None else None


def fetch_stats(api_fixture_id: int, provider: Provider | None = None) -> bool:
    """Fetch advanced stats for a fixture and write them onto its ``matches`` row.

    Returns:
        True if stats were written, False if disabled, the fixture is unknown
        locally, or the provider had nothing for it.
    """
    settings = get_settings()
    if provider is None and not settings.stats_provider:
        log.info("STATS_PROVIDER not configured — skipping stats for %d", api_fixture_id)
        return False
    active = provider or build_provider(settings.stats_provider)

    with session_scope() as session:
        match = session.scalar(
            select(Match).where(Match.api_fixture_id == api_fixture_id)
        )
        if match is None:
            log.warning("Fixture %d not in DB — run match sync first", api_fixture_id)
            return False

        stats = active.get_advanced_stats(api_fixture_id)
        if stats is None:
            log.warning("No advanced stats returned for fixture %d", api_fixture_id)
            return False

        match.xg_home = _dec2(stats.xg_home)
        match.xg_away = _dec2(stats.xg_away)
        match.possession_home = _dec2(stats.possession_home)
        match.possession_away = _dec2(stats.possession_away)

    log.info("Stored advanced stats for fixture %d", api_fixture_id)
    return True
