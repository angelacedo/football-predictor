# football-predictor

Football 1X2 prediction + paper-betting bot. Predicts probabilities, tracks
them against real results, scores accuracy (Brier/log loss), and evaluates a
value-betting strategy in backtest — **no real money is ever moved.**

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in at least FOOTBALL_API_KEY + DATABASE_URL
python scripts/init_db.py
```

## Flow

```
train_model.py -> predict_upcoming.py + fetch_odds.py -> (match ends) ->
validate_predictions.py -> run_backtest.py
```

## Multi-algorithm training

`ml/train.py` has three registered algorithms (`MODEL_REGISTRY`): `baseline`
(logistic regression), `xgboost`, `random_forest`. Models are trained per
league, artifact-named `"{algorithm}_{league}"` (e.g. `xgboost_La_Liga`):

```bash
python scripts/train_all.py --leagues "La Liga" "Premier League" \
    --algorithms baseline xgboost --workers 4
```

Defaults come from `.env`'s `LEAGUES`/`ACTIVE_ALGORITHMS`/`TRAIN_WORKERS`.
`ml/predict.py`'s `predict_ensemble()` averages `predict_proba` across
whichever of a league's algorithms are actually registered — use it once
`/models` (below) shows an algorithm actually beats `baseline`'s Brier score;
until then a single model is simpler and just as good.

## Docker

```bash
cp .env.example .env   # fill in provider keys; DATABASE_URL is overridden by compose
docker compose up -d db
docker compose run --rm app python scripts/init_db.py
docker compose run --rm app python scripts/train_model.py
docker compose run --rm app python scripts/predict_upcoming.py
docker compose run --rm app python scripts/fetch_odds.py
docker compose run --rm app python scripts/validate_predictions.py
docker compose run --rm app python scripts/run_backtest.py
```

Scripts are one-shot CLI jobs, not a server — `app`'s default command
(`predict_upcoming.py`) is just a placeholder; run any script via
`docker compose run --rm app python scripts/<name>.py`. `models/` is bind-mounted
so trained artifacts survive container rebuilds.

## Scheduler

`scripts/run_scheduler.py` is the **one** long-running exception to "scripts
are one-shot CLI jobs" — a 4th compose service (`scheduler`, same image as
`app`) that runs sync/train/predict/validate in-process, on a schedule,
forever. No `docker compose run` invocations needed once it's deployed — see
`docker-compose.prod.yml`'s `scheduler` service.

| Job | Schedule |
|---|---|
| Sync + predict | daily 04:00 UTC (current + next season, per league; World Cup included) |
| Validate (+ retrain check) | daily 06:00 UTC |
| Train | weekly, Mon 05:00 UTC |
| Backtest | weekly, Mon 06:00 UTC, informational |

`/status` on the dashboard shows the last run (`SUCCESS`/`ERROR`/`SKIPPED`)
of every job — an expected skip is logged as its own `SKIPPED` row, not
indistinguishable from a silent failure.

### Production (VPS)

`docker-compose.prod.yml` pulls pre-built images
(`ghcr.io/angelacedo/football-predictor:latest` / `-web:latest`, published by
`.github/workflows/docker-publish.yml` on every push to `main`) instead of
building from source — the deploy target has no copy of this repo.
`docker compose -f docker-compose.prod.yml run --rm app python
scripts/<name>.py` for one-off manual runs, same as local usage. Requires a
real `.env` next to the compose file for `${VAR}` substitution.

**Deploy safety**: any redeploy must include `db`+`app`+`scheduler`+`web`
together — a partial redeploy (e.g. `db`+`app` only, to run a one-off script)
silently tears down `web` and `scheduler`, causing real dashboard downtime
(happened once, 2026-07-05).

Deployed via the Hostinger MCP server (`VPS_createNewProjectV1`) — that
deploy path does **not** honor `env_file:`, only an inline `environment:`
block in the compose YAML actually sent, so secrets must be passed as literal
values in that call rather than relying on a separate `.env` on the VPS.

## Dashboard

`web/` is a separate FastAPI + Jinja2 + HTMX app — **read-only, GET-only,
zero mutation** — reading the same DB the bot writes to. Its own `Dockerfile`
and image (`ghcr.io/angelacedo/football-predictor-web`); depends on `footy`
as a library only, doesn't touch `src/footy/` behavior.

| Route | Shows |
|---|---|
| `/` | Match/prediction counts, synced leagues |
| `/predictions` | Upcoming (`SCHEDULED`) matches + probabilities, filterable by league |
| `/models` | Brier/log-loss/accuracy per (league, algorithm) — `predictions.metrics.breakdown_by_league_and_model` |

Local: `docker compose up -d` then open `http://localhost:8000`. Production:
deployed alongside `app`/`db` in the same compose project (same Docker
network, reaches `db` by service name — no port published), routed by the
existing Traefik instance via labels (`Host(\`footy.stackmint.cloud\`)`,
`certresolver=letsencrypt`, no auth middleware for now).

## Providers

Ingestion is provider-agnostic: `matches.py`/`odds.py`/`stats.py` only consume
normalized DTOs (`FixtureDTO`, `OddsDTO`, `AdvancedStatsDTO` in
`ingest/schemas.py`) — never a specific API's JSON shape. Each provider lives
in `ingest/providers/<name>.py` and implements the `Provider` protocol
(`ingest/providers/base.py`); `ingest/providers/registry.py` builds one by
name.

| Provider | Fixtures | Odds | Advanced stats (xG, possession) |
|---|---|---|---|
| `api_football` | ✅ | ✅ | — |
| `sportmonks` | ✅ | — | ✅ |
| `thestatsapi` | — | — | ✅ |
| `the_odds_api` | — | ✅ (multi-book) | — |

Select via `.env`:

```bash
FIXTURES_PROVIDER=api_football
ODDS_PROVIDER_PRIMARY=api_football
ODDS_PROVIDER_FALLBACK=the_odds_api   # optional; empty disables fallback
STATS_PROVIDER=                       # optional; empty disables xG/possession
```

**Fallback:** `fetch_odds()` tries `ODDS_PROVIDER_PRIMARY` first; if it raises
or returns no odds, it tries `ODDS_PROVIDER_FALLBACK` (when set). A default
install with only `FOOTBALL_API_KEY` set behaves exactly as before this
feature — `api_football` alone satisfies both fixtures and odds.

**Cross-provider odds matching:** API-Football keys odds by its own numeric
fixture id; The Odds API has no shared id scheme and is matched by
`(home_team, away_team)` + a kickoff-time tolerance window instead
(`OddsQuery` in `schemas.py` carries both). If you mix providers with
different team-name spellings, matching can silently miss — the adapter logs
a warning rather than failing loudly.

**xG/possession:** persisted onto `matches.xg_home/xg_away/possession_home/
possession_away` via `ingest/stats.py`, but **not yet consumed** by
`ml/features.py` — add that once there's a labeled backlog to validate it
against.

**Adding a provider:** implement `Provider` in a new
`ingest/providers/<name>.py` (mix in `UnsupportedProviderMixin` and override
only the capabilities you have), register it in `registry.py`'s `_BUILDERS`,
add its config fields to `config.py`.

## Testing

```bash
pytest          # all mocked, no network / no live DB required for provider tests
ruff check .
mypy
```

`tests/test_web.py` needs the `web` extra (`pip install -e ".[dev,web]"`) —
skipped automatically otherwise, not a failure.

## Compliance

Paper/backtest only. No real-money execution. See code comments in
`betting/` for the rationale.
