"""joblog.record() writes job_runs rows correctly."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from joblog import JobLogBase, JobRun, record


@pytest.fixture
def jobs_db(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/joblog_test.db")
    import footy.config as config
    import footy.db as db

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()

    JobLogBase.metadata.create_all(db.get_engine())
    yield
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db._session_factory.cache_clear()


def test_record_writes_row(jobs_db: None) -> None:
    from footy.db import session_scope

    record("football_sync", "SUCCESS", "La Liga: seasons 2025,2026")

    with session_scope() as session:
        rows = session.query(JobRun).all()
        assert len(rows) == 1
        assert rows[0].job_name == "football_sync"
        assert rows[0].status == "SUCCESS"
        assert rows[0].detail == "La Liga: seasons 2025,2026"
        assert rows[0].finished_at is not None


def test_record_multiple_jobs_independent(jobs_db: None) -> None:
    from footy.db import session_scope

    record("football_sync", "ERROR", "La Liga: boom")
    record("football_predict", "SUCCESS")

    with session_scope() as session:
        rows = {r.job_name: r for r in session.query(JobRun).all()}
        assert rows["football_sync"].status == "ERROR"
        assert rows["football_predict"].status == "SUCCESS"
