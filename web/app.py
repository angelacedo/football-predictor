"""Read-only ops dashboard for football-predictor.

GET-only, zero mutation — reads the same DB the bot writes to, never writes
back. Separate container/image from the core `footy`/`sports` packages;
depends on them as libraries only.
"""

from __future__ import annotations

from pathlib import Path

from badges import color_for, initials, readable_text_color
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from metrics_color import brier_color, log_loss_color
from sqlalchemy import func, select

from footy.data import validated_predictions_dataframe
from footy.db import session_scope
from footy.orm import Match, Prediction
from footy.predictions.metrics import breakdown_by_league_and_model
from joblog import JobRun

app = FastAPI(title="football-predictor dashboard")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.globals["badge_color"] = color_for
templates.env.globals["badge_text_color"] = readable_text_color
templates.env.globals["badge_initials"] = initials
templates.env.globals["brier_color"] = brier_color
templates.env.globals["log_loss_color"] = log_loss_color


def _leagues() -> list[str]:
    with session_scope() as session:
        return sorted(session.scalars(select(Match.league).distinct()).all())


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict[str, dict[str, str | None]]:
    """Last run of every distinct job_name - so scheduler health is checkable
    without SSH or guessing. An expected skip shows as its own SKIPPED status
    here, not indistinguishable from a silent failure."""
    with session_scope() as session:
        job_names = session.scalars(select(JobRun.job_name).distinct()).all()
        result: dict[str, dict[str, str | None]] = {}
        for name in job_names:
            latest = session.scalar(
                select(JobRun).where(JobRun.job_name == name).order_by(JobRun.id.desc())
            )
            if latest is not None:
                result[name] = {
                    "status": latest.status,
                    "finished_at": latest.finished_at.isoformat() if latest.finished_at else None,
                    "detail": latest.detail,
                }
    return result


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    with session_scope() as session:
        n_matches = session.scalar(select(func.count(Match.id))) or 0
        n_scheduled = session.scalar(
            select(func.count(Match.id)).where(Match.status == "SCHEDULED")
        ) or 0
        n_predictions = session.scalar(select(func.count(Prediction.id))) or 0
        n_validated = session.scalar(
            select(func.count(Prediction.id)).where(Prediction.validated_at.is_not(None))
        ) or 0
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "active": "overview",
            "leagues": _leagues(),
            "n_matches": n_matches,
            "n_scheduled": n_scheduled,
            "n_predictions": n_predictions,
            "n_validated": n_validated,
        },
    )


@app.get("/predictions", response_class=HTMLResponse)
def predictions(request: Request, league: str | None = None) -> HTMLResponse:
    with session_scope() as session:
        query = (
            select(
                Match.kickoff, Match.league, Match.home_team, Match.away_team,
                Prediction.model_name, Prediction.prob_home_win,
                Prediction.prob_draw, Prediction.prob_away_win,
            )
            .join(Prediction, Prediction.match_id == Match.id)
            .where(Match.status == "SCHEDULED")
            .order_by(Match.kickoff)
        )
        if league:
            query = query.where(Match.league == league)
        rows = session.execute(query).all()
    return templates.TemplateResponse(
        request,
        "predictions.html",
        {"active": "predictions", "sport": "football", "rows": rows,
         "leagues": _leagues(), "selected_league": league},
    )


@app.get("/models", response_class=HTMLResponse)
def models(request: Request) -> HTMLResponse:
    rows = breakdown_by_league_and_model(validated_predictions_dataframe())
    return templates.TemplateResponse(
        request, "models.html", {"active": "models", "rows": rows}
    )
