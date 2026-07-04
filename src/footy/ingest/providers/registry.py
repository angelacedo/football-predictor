"""Build a provider instance by name.

One place mapping the config strings (``fixtures_provider``,
``odds_provider_primary``/``_fallback``, ``stats_provider``) to adapter
classes, so ``matches.py``/``odds.py``/``stats.py`` don't each duplicate the
same if/elif.
"""

from __future__ import annotations

from collections.abc import Callable

from footy.ingest.providers.api_football import ApiFootballProvider
from footy.ingest.providers.base import Provider, ProviderError
from footy.ingest.providers.oddalerts import OddAlertsProvider
from footy.ingest.providers.sportmonks import SportmonksProvider
from footy.ingest.providers.the_odds_api import TheOddsApiProvider
from footy.ingest.providers.thestatsapi import TheStatsApiProvider

_BUILDERS: dict[str, Callable[[], Provider]] = {
    "api_football": ApiFootballProvider,
    "sportmonks": SportmonksProvider,
    "thestatsapi": TheStatsApiProvider,
    "the_odds_api": TheOddsApiProvider,
    "oddalerts": OddAlertsProvider,
}


def build_provider(name: str) -> Provider:
    """Construct the provider adapter registered under ``name``.

    Raises:
        ProviderError: if ``name`` isn't a known provider.
    """
    builder = _BUILDERS.get(name)
    if builder is None:
        raise ProviderError(f"Unknown provider '{name}'; known: {sorted(_BUILDERS)}")
    return builder()
