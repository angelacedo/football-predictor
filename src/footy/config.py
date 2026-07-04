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


class Settings(BaseSettings):
    """Typed application configuration.

    Attributes:
        football_api_key: API-Football key (fixtures, results, odds).
        football_api_base: API-Football base URL.
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
    database_url: str = Field(
        default="postgresql+psycopg://footy:footy@localhost:5432/footy"
    )
    model_dir: str = Field(default="models")
    edge_threshold: float = Field(default=0.05)
    kelly_fraction: float = Field(default=0.25)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached settings instance."""
    return Settings()
