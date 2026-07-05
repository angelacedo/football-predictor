"""Scheduler run observability - own DeclarativeBase, sport-agnostic.

Not under footy/ or sports/: job_runs tracks the scheduler itself (every
sport's jobs, plus the scheduler process's own lifecycle), not one sport's
data. Shares the same Postgres instance via footy.db.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from footy.db import session_scope


class JobLogBase(DeclarativeBase):
    """Declarative base for scheduler observability models."""


class JobRun(JobLogBase):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(60))
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(10))  # SUCCESS | ERROR | SKIPPED
    detail: Mapped[str | None] = mapped_column(Text, default=None)

    def __repr__(self) -> str:
        return f"<JobRun id={self.id} job={self.job_name} status={self.status}>"


def record(job_name: str, status: str, detail: str = "") -> None:
    """Write one job_runs row. status: SUCCESS | ERROR | SKIPPED.

    finished_at is set immediately (jobs here are logged after completion, not
    tracked as in-progress) - simpler than a two-phase start/finish update for
    the batch-style jobs this scheduler runs.
    """
    with session_scope() as session:
        session.add(
            JobRun(
                job_name=job_name, finished_at=datetime.now(), status=status, detail=detail
            )
        )
