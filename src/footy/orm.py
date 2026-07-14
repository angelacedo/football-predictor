"""SQLAlchemy ORM models mirroring schema.sql.

The raw schema.sql remains the source of truth for DDL (see scripts/init_db.py);
these classes are the typed access layer used by the rest of the app.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_fixture_id: Mapped[int] = mapped_column(unique=True)
    league: Mapped[str] = mapped_column(String(80))
    season: Mapped[int]
    home_team: Mapped[str] = mapped_column(String(80))
    away_team: Mapped[str] = mapped_column(String(80))
    kickoff: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(10), default="SCHEDULED")
    home_goals: Mapped[int | None] = mapped_column(default=None)
    away_goals: Mapped[int | None] = mapped_column(default=None)
    xg_home: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    xg_away: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    possession_home: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    possession_away: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    round: Mapped[str | None] = mapped_column(String(40), default=None)
    winner_home: Mapped[bool | None] = mapped_column(Boolean, default=None)
    winner_away: Mapped[bool | None] = mapped_column(Boolean, default=None)

    def __repr__(self) -> str:
        return (
            f"<Match id={self.id} {self.home_team} vs {self.away_team} "
            f"status={self.status}>"
        )


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("match_id", "model_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    model_name: Mapped[str] = mapped_column(String(50))
    prediction_date: Mapped[datetime] = mapped_column(server_default=func.now())
    prob_home_win: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    prob_draw: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    prob_away_win: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    predicted_score_home: Mapped[int | None] = mapped_column(default=None)
    predicted_score_away: Mapped[int | None] = mapped_column(default=None)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), default=None)

    actual_score_home: Mapped[int | None] = mapped_column(default=None)
    actual_score_away: Mapped[int | None] = mapped_column(default=None)
    actual_result: Mapped[str | None] = mapped_column(String(10), default=None)
    brier_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), default=None)
    log_loss: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), default=None)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, default=None)
    validated_at: Mapped[datetime | None] = mapped_column(default=None)

    def __repr__(self) -> str:
        return (
            f"<Prediction id={self.id} match={self.match_id} "
            f"model={self.model_name} validated={self.validated_at is not None}>"
        )


class Odds(Base):
    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    bookmaker: Mapped[str] = mapped_column(String(60))
    odds_home: Mapped[Decimal] = mapped_column(Numeric(7, 3))
    odds_draw: Mapped[Decimal] = mapped_column(Numeric(7, 3))
    odds_away: Mapped[Decimal] = mapped_column(Numeric(7, 3))
    captured_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_closing: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return (
            f"<Odds id={self.id} match={self.match_id} book={self.bookmaker} "
            f"{self.odds_home}/{self.odds_draw}/{self.odds_away}>"
        )


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"))
    odds_id: Mapped[int] = mapped_column(ForeignKey("odds.id"))
    selection: Mapped[str] = mapped_column(String(10))
    model_prob: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    market_odds: Mapped[Decimal] = mapped_column(Numeric(7, 3))
    edge: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    stake: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    staking_method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10), default="OPEN")
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), default=None)
    placed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    settled_at: Mapped[datetime | None] = mapped_column(default=None)

    def __repr__(self) -> str:
        return (
            f"<Bet id={self.id} pred={self.prediction_id} sel={self.selection} "
            f"stake={self.stake} status={self.status}>"
        )
