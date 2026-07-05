"""Read-only ops dashboard for football-predictor.

GET-only, zero mutation — reads the same DB the bot writes to, never writes
back. Separate container/image from the core `footy` package; depends on it
as a library only.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from footy.data import validated_predictions_dataframe
from footy.db import session_scope
from footy.orm import Match, Prediction
from footy.predictions.metrics import breakdown_by_league_and_model

app = FastAPI(title="football-predictor dashboard")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _leagues() -> list[str]:
    with session_scope() as session:
        return sorted(session.scalars(select(Match.league).distinct()).all())


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
    return templates.TemplateResponse(
        request,
        "index.html",
        {
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
        {"rows": rows, "leagues": _leagues(), "selected_league": league},
    )


@app.get("/models", response_class=HTMLResponse)
def models(request: Request) -> HTMLResponse:
    rows = breakdown_by_league_and_model(validated_predictions_dataframe())
    return templates.TemplateResponse(request, "models.html", {"rows": rows})
