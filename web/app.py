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
from sports.f1.orm import F1Entry, F1Prediction, F1Session

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


def _f1_sessions() -> list[F1Session]:
    with session_scope() as session:
        return list(session.scalars(select(F1Session).order_by(F1Session.start_time.desc())).all())


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


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
        n_f1_sessions = session.scalar(select(func.count(F1Session.id))) or 0
        n_f1_scheduled = session.scalar(
            select(func.count(F1Session.id)).where(F1Session.status == "SCHEDULED")
        ) or 0
        n_f1_predictions = session.scalar(select(func.count(F1Prediction.id))) or 0
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
            "n_f1_sessions": n_f1_sessions,
            "n_f1_scheduled": n_f1_scheduled,
            "n_f1_predictions": n_f1_predictions,
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


@app.get("/f1/sessions", response_class=HTMLResponse)
def f1_sessions(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "f1_sessions.html",
        {"active": "sessions", "sport": "f1", "sessions": _f1_sessions()},
    )


@app.get("/f1/predictions", response_class=HTMLResponse)
def f1_predictions(request: Request, session_id: int | None = None) -> HTMLResponse:
    sessions = _f1_sessions()
    if session_id is None:
        scheduled = [s for s in sessions if s.status == "SCHEDULED"]
        chosen = scheduled[-1] if scheduled else (sessions[0] if sessions else None)
    else:
        chosen = next((s for s in sessions if s.id == session_id), None)

    rows: list[dict[str, object]] = []
    if chosen is not None:
        with session_scope() as session:
            entries = {
                e.driver_number: e
                for e in session.scalars(
                    select(F1Entry).where(F1Entry.session_id == chosen.id)
                ).all()
            }
            preds = session.scalars(
                select(F1Prediction)
                .where(F1Prediction.session_id == chosen.id)
                .order_by(F1Prediction.predicted_position)
            ).all()
        for p in preds:
            entry = entries.get(p.driver_number)
            rows.append(
                {
                    "driver_number": p.driver_number,
                    "driver_name": entry.driver_name if entry else f"#{p.driver_number}",
                    "team": entry.team if entry else "",
                    "team_colour": f"#{entry.team_colour}" if entry and entry.team_colour else None,
                    "predicted_position": float(p.predicted_position),
                    "actual_position": entry.finish_position if entry else None,
                }
            )
    return templates.TemplateResponse(
        request,
        "f1_predictions.html",
        {
            "active": "predictions", "sport": "f1", "sessions": sessions,
            "chosen": chosen, "rows": rows,
        },
    )
