"""Application settings loaded from environment / .env.

Example:
    >>> from footy.config import get_settings
    >>> s = get_settings()
    >>> s.edge_threshold
    0.05
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Providers that can serve odds, keyed by the value used in
# odds_provider_primary/odds_provider_fallback, mapped to the Settings field
# holding that provider's API key. Used only to validate the *odds* path
# (require_odds_provider) — unrelated scripts (init_db, train_model) never
# touch this, so they keep working with zero provider keys set, same as today.
_ODDS_PROVIDER_KEY_FIELDS = {
    "api_football": "football_api_key",
    "the_odds_api": "the_odds_api_key",
}


class Settings(BaseSettings):
    """Typed application configuration.

    Attributes:
        football_api_key: API-Football key (fixtures, results, odds).
        football_api_base: API-Football base URL.
        sportmonks_api_key: Sportmonks key (fixtures, advanced stats).
        sportmonks_api_base: Sportmonks base URL.
        thestatsapi_key: TheStatsAPI key (advanced stats).
        thestatsapi_base: TheStatsAPI base URL.
        the_odds_api_key: The Odds API key (multi-bookmaker odds).
        the_odds_api_base: The Odds API base URL.
        the_odds_api_sport_key: The Odds API sport key, e.g. 'soccer_epl'.
        fixtures_provider: Provider name used for fixtures/results sync.
        odds_provider_primary: Provider name tried first for odds.
        odds_provider_fallback: Provider name tried if the primary fails or
            returns nothing; empty string disables fallback.
        stats_provider: Provider name for advanced stats (xG/possession);
            empty string disables stats fetching entirely.
        database_url: SQLAlchemy connection URL (psycopg3 driver).
        model_dir: Directory holding joblib model artifacts.
        edge_threshold: Minimum value edge to select a paper bet.
        kelly_fraction: Fractional-Kelly multiplier (0..1); 1.0 = full Kelly.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    football_api_key: str = Field(default="")
    football_api_base: str = Field(default="https://v3.football.api-sports.io")

    sportmonks_api_key: str = Field(default="")
    sportmonks_api_base: str = Field(default="https://api.sportmonks.com/v3/football")

    thestatsapi_key: str = Field(default="")
    thestatsapi_base: str = Field(default="https://api.thestatsapi.com/v1")

    the_odds_api_key: str = Field(default="")
    the_odds_api_base: str = Field(default="https://api.the-odds-api.com/v4")
    the_odds_api_sport_key: str = Field(default="soccer_epl")

    fixtures_provider: str = Field(default="api_football")
    odds_provider_primary: str = Field(default="api_football")
    odds_provider_fallback: str = Field(default="")
    stats_provider: str = Field(default="")

    database_url: str = Field(
        default="postgresql+psycopg://footy:footy@localhost:5432/footy"
    )
    model_dir: str = Field(default="models")
    edge_threshold: float = Field(default=0.05)
    kelly_fraction: float = Field(default=0.25)

    def require_odds_provider(self) -> None:
        """Raise if neither the primary nor the fallback odds provider has a key set.

        Called from the odds-ingestion path only (see ``footy.ingest.odds``),
        not from ``get_settings()`` itself — scripts that never touch odds
        (``init_db.py``, ``train_model.py``) must keep working with zero
        provider keys configured, exactly as before this feature.
        """
        for provider in (self.odds_provider_primary, self.odds_provider_fallback):
            key_field = _ODDS_PROVIDER_KEY_FIELDS.get(provider)
            if key_field and getattr(self, key_field):
                return
        raise RuntimeError(
            "No odds provider is configured with an API key. Set ODDS_PROVIDER_PRIMARY "
            "(and optionally ODDS_PROVIDER_FALLBACK) to one of "
            f"{sorted(_ODDS_PROVIDER_KEY_FIELDS)} and its matching *_KEY."
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached settings instance."""
    return Settings()
