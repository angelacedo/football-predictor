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

## Compliance

Paper/backtest only. No real-money execution. See code comments in
`betting/` for the rationale.
