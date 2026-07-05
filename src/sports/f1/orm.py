"""SQLAlchemy ORM models for F1 - own DeclarativeBase, f1_-prefixed tables.

Shares the same Postgres instance/engine as footy (confirmed: no separate DB),
but a separate Base so F1's schema evolves independently of footy.orm.Base.
See schema.sql for the raw DDL these mirror.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class F1Base(DeclarativeBase):
    """Declarative base for all F1 ORM models."""


class F1Session(F1Base):
    __tablename__ = "f1_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_session_id: Mapped[int] = mapped_column(unique=True)
    season: Mapped[int]
    round: Mapped[int]
    circuit: Mapped[str] = mapped_column(String(80))
    session_type: Mapped[str] = mapped_column(String(12))  # RACE | QUALIFYING | SPRINT
    start_time: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(10), default="SCHEDULED")  # SCHEDULED | FINISHED

    def __repr__(self) -> str:
        return f"<F1Session id={self.id} {self.circuit} {self.session_type} status={self.status}>"


class F1Entry(F1Base):
    __tablename__ = "f1_entries"
    __table_args__ = (UniqueConstraint("session_id", "driver_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("f1_sessions.id"))
    driver_number: Mapped[int]
    driver_name: Mapped[str] = mapped_column(String(80))
    team: Mapped[str] = mapped_column(String(80))
    grid_position: Mapped[int | None] = mapped_column(default=None)
    finish_position: Mapped[int | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(10), default="FINISHED")  # FINISHED|DNF|DNS|DSQ
    points: Mapped[Decimal | None] = mapped_column(default=None)

    def __repr__(self) -> str:
        return (
            f"<F1Entry id={self.id} driver={self.driver_number} "
            f"finish={self.finish_position} status={self.status}>"
        )


class F1Prediction(F1Base):
    __tablename__ = "f1_predictions"
    __table_args__ = (UniqueConstraint("session_id", "driver_number", "model_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("f1_sessions.id"))
    driver_number: Mapped[int]
    model_name: Mapped[str] = mapped_column(String(50))
    prediction_date: Mapped[datetime] = mapped_column(server_default=func.now())
    predicted_position: Mapped[Decimal] = mapped_column()

    actual_position: Mapped[int | None] = mapped_column(default=None)
    mae_position: Mapped[Decimal | None] = mapped_column(default=None)
    validated_at: Mapped[datetime | None] = mapped_column(default=None)

    def __repr__(self) -> str:
        return (
            f"<F1Prediction id={self.id} session={self.session_id} "
            f"driver={self.driver_number} model={self.model_name}>"
        )
