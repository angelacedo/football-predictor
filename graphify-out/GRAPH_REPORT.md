# Graph Report - .  (2026-07-05)

## Corpus Check
- Corpus is ~13,320 words - fits in a single context window. You may not need a graph.

## Summary
- 493 nodes · 852 edges · 32 communities (30 shown, 2 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 175 edges (avg confidence: 0.74)
- Token cost: 60,469 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Provider Ingestion Protocol|Provider Ingestion Protocol]]
- [[_COMMUNITY_The Odds API Provider|The Odds API Provider]]
- [[_COMMUNITY_Prediction Metrics|Prediction Metrics]]
- [[_COMMUNITY_Multi-Algorithm Training|Multi-Algorithm Training]]
- [[_COMMUNITY_Ensemble Prediction|Ensemble Prediction]]
- [[_COMMUNITY_Config & Training CLI|Config & Training CLI]]
- [[_COMMUNITY_API-Football Client|API-Football Client]]
- [[_COMMUNITY_Value Betting|Value Betting]]
- [[_COMMUNITY_ORM & Backtest Script|ORM & Backtest Script]]
- [[_COMMUNITY_Database Engine Setup|Database Engine Setup]]
- [[_COMMUNITY_Backtest Engine|Backtest Engine]]
- [[_COMMUNITY_Feature Engineering|Feature Engineering]]
- [[_COMMUNITY_Deployment & Web Templates|Deployment & Web Templates]]
- [[_COMMUNITY_Staking Strategy|Staking Strategy]]
- [[_COMMUNITY_Data Loading & Scripts|Data Loading & Scripts]]
- [[_COMMUNITY_Bankroll Management|Bankroll Management]]
- [[_COMMUNITY_Ingestion DTOs & Schemas|Ingestion DTOs & Schemas]]
- [[_COMMUNITY_Dashboard Web App|Dashboard Web App]]
- [[_COMMUNITY_Prediction Tracker|Prediction Tracker]]
- [[_COMMUNITY_Prediction Validator|Prediction Validator]]
- [[_COMMUNITY_Odds Ingestion|Odds Ingestion]]
- [[_COMMUNITY_Model Registry Concepts|Model Registry Concepts]]
- [[_COMMUNITY_Advanced Stats Ingestion|Advanced Stats Ingestion]]
- [[_COMMUNITY_Compliance|Compliance]]
- [[_COMMUNITY_Package Metadata (footy)|Package Metadata (footy)]]

## God Nodes (most connected - your core abstractions)
1. `OddsQuery` - 21 edges
2. `session_scope()` - 17 edges
3. `SportmonksProvider` - 16 edges
4. `FakeResponse` - 16 edges
5. `get_settings()` - 15 edges
6. `ApiFootballProvider` - 15 edges
7. `ProviderError` - 14 edges
8. `Provider` - 14 edges
9. `FixtureDTO` - 14 edges
10. `MatchProbs` - 14 edges

## Surprising Connections (you probably didn't know these)
- `app service (docker-compose.prod.yml, prebuilt image)` --semantically_similar_to--> `app service (docker-compose.yml, builds locally)`  [INFERRED] [semantically similar]
  docker-compose.prod.yml → docker-compose.yml
- `web service (docker-compose.prod.yml, Traefik-routed)` --semantically_similar_to--> `web service (docker-compose.yml, builds locally)`  [INFERRED] [semantically similar]
  docker-compose.prod.yml → docker-compose.yml
- `db service (docker-compose.prod.yml, postgres)` --semantically_similar_to--> `db service (docker-compose.yml, postgres)`  [INFERRED] [semantically similar]
  docker-compose.prod.yml → docker-compose.yml
- `main()` --calls--> `session_scope()`  [INFERRED]
  scripts/fetch_odds.py → src/footy/db.py
- `main()` --calls--> `fetch_odds()`  [INFERRED]
  scripts/fetch_odds.py → src/footy/ingest/odds.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Local docker-compose stack (db, app, web)** — docker_compose_db, docker_compose_app, docker_compose_web [EXTRACTED 1.00]
- **Production docker-compose stack (db, app, web) behind Traefik** — docker_compose_prod_db, docker_compose_prod_app, docker_compose_prod_web [EXTRACTED 1.00]
- **Jinja2 template inheritance from base.html** — web_templates_base_base, web_templates_index_index, web_templates_models_models, web_templates_predictions_predictions [EXTRACTED 1.00]

## Communities (32 total, 2 thin omitted)

### Community 0 - "Provider Ingestion Protocol"
Cohesion: 0.06
Nodes (39): Exception, Protocol, main(), Sync fixtures/results for a league/season into ``matches``.  Usage:     python s, Fetch all fixtures for a league/season and upsert them.      Args:         leagu, sync_league(), Provider, ProviderError (+31 more)

### Community 1 - "The Odds API Provider"
Cohesion: 0.06
Nodes (36): datetime, Common contract every data provider adapter satisfies.  A provider does not have, Normalize a datetime to naive UTC for cross-provider comparison.      ``matches., to_naive_utc(), _matches_event(), _odds_from_event(), Any, The Odds API provider adapter — multi-bookmaker 1X2 odds.  Docs: https://the-odd (+28 more)

### Community 2 - "Prediction Metrics"
Cohesion: 0.07
Nodes (43): Probs, breakdown_by(), breakdown_by_league_and_model(), brier_score(), calibration_by_class(), log_loss_single(), mean_brier(), mean_log_loss() (+35 more)

### Community 3 - "Multi-Algorithm Training"
Cohesion: 0.09
Nodes (28): BaseEstimator, ClassifierMixin, Pipeline, Series, build_pipeline(), build_random_forest_pipeline(), build_xgboost_pipeline(), _LabelEncodedXGBClassifier (+20 more)

### Community 4 - "Ensemble Prediction"
Cohesion: 0.12
Nodes (29): DummyClassifier, predict_ensemble(), predict_ensemble_from_history(), predict_match(), _probs_from_model(), Any, DataFrame, Produce 1X2 probabilities from a trained model.  Example:     >>> probs = MatchP (+21 more)

### Community 5 - "Config & Training CLI"
Cohesion: 0.08
Nodes (22): BaseSettings, CaptureFixture, main(), Train models for multiple leagues/algorithms in parallel.  Usage:     python scr, Run the training sweep and print every result.      Returns:         1 if any re, get_settings(), Raise if neither the primary nor the fallback odds provider has a key set., Return the process-wide cached settings instance. (+14 more)

### Community 6 - "API-Football Client"
Cohesion: 0.10
Nodes (17): ApiFootball, Any, Thin API-Football (v3) HTTP client.  Docs: https://www.api-football.com/document, Minimal wrapper returning the ``response`` array of an API-Football call., GET ``/{path}`` and return the ``response`` list.          Retries transport err, ApiFootballProvider, _fixture_from_json(), _match_winner_odds() (+9 more)

### Community 7 - "Value Betting"
Cohesion: 0.12
Nodes (18): edge(), find_value_bet(), implied_probs(), Value detection: compare model probabilities to bookmaker odds.  A bet has posit, A selected value bet (paper only — never placed)., Expected value per unit staked minus 1: ``model_prob * odds - 1``., Overround-normalized market probabilities from 1X2 decimal odds., Return the highest-edge selection clearing ``threshold``, or None.      Args: (+10 more)

### Community 8 - "ORM & Backtest Script"
Cohesion: 0.16
Nodes (13): DeclarativeBase, build_settled_bets(), main(), _odds_for(), Paper backtest: turn validated predictions + odds into value bets and score them, Return (any pre-match odds, closing odds) rows for a match., Base, Bet (+5 more)

### Community 9 - "Database Engine Setup"
Cohesion: 0.14
Nodes (15): Engine, main(), Initialize the database by executing schema.sql.  Usage:     python scripts/init, Session, sessionmaker, Application settings loaded from environment / .env.  Example:     >>> from foot, get_engine(), Database engine and session factory.  Example:     >>> from footy.db import sess (+7 more)

### Community 10 - "Backtest Engine"
Cohesion: 0.18
Nodes (14): backtest(), BacktestReport, Replay settled paper bets into performance stats.  Answers "do I actually have a, A resolved paper bet. ``closing_odds`` optional, enables CLV., Profit/loss: ``stake*(odds-1)`` on a win, ``-stake`` on a loss., Aggregate paper-betting performance., Compute ROI, hit-rate, max drawdown and CLV over ``bets``., SettledBet (+6 more)

### Community 11 - "Feature Engineering"
Cohesion: 0.19
Nodes (14): _avg(), compute_feature_frame(), DataFrame, Feature engineering for 1X2 prediction.  Features are **leakage-safe by construc, Map a final score to a 1X2 label., Compute leakage-safe features for every row in ``df``.      Args:         df: Ma, result_from_goals(), _matches() (+6 more)

### Community 12 - "Deployment & Web Templates"
Cohesion: 0.23
Nodes (15): build-push job (docker-publish.yml), web-build-push job (docker-publish.yml), app service (docker-compose.yml, builds locally), db service (docker-compose.yml, postgres), app service (docker-compose.prod.yml, prebuilt image), db service (docker-compose.prod.yml, postgres), web service (docker-compose.prod.yml, Traefik-routed), web service (docker-compose.yml, builds locally) (+7 more)

### Community 13 - "Staking Strategy"
Cohesion: 0.21
Nodes (12): flat_stake(), kelly_fraction(), kelly_stake(), Stake sizing. Paper only — computes amounts, never moves money.  Two methods:  *, Fixed fraction of bankroll (default 1%)., Fractional-Kelly bankroll fraction for a bet.      ``f* = (b*p - q) / b`` with `, Stake amount from fractional Kelly on ``bankroll``., Stake sizing: flat and fractional Kelly. (+4 more)

### Community 14 - "Data Loading & Scripts"
Cohesion: 0.19
Nodes (10): main(), Predict all SCHEDULED matches and record the predictions.  Idempotent: re-runnin, main(), Train the baseline model from matches in the DB.  Usage:     python scripts/trai, matches_dataframe(), DataFrame, Load DB rows into pandas frames for the ML layer., Return matches as a DataFrame with the columns the feature builder needs.      A (+2 more)

### Community 15 - "Bankroll Management"
Cohesion: 0.17
Nodes (6): Bankroll, Bankroll and risk limits for paper betting.  Caps a desired stake by (a) a per-b, Stateful paper bankroll with per-bet and per-group exposure caps., Return ``desired`` clamped by per-bet and remaining group-exposure caps., Reserve ``stake`` of open exposure for ``group``; returns the stake., Apply a settled bet: credit pnl and release the reserved exposure.

### Community 16 - "Ingestion DTOs & Schemas"
Cohesion: 0.20
Nodes (10): config.py (provider config fields), Provider protocol (ingest/providers/base.py), provider registry _BUILDERS (ingest/providers/registry.py), AdvancedStatsDTO (ingest/schemas.py), FixtureDTO (ingest/schemas.py), OddsDTO (ingest/schemas.py), OddsQuery (ingest/schemas.py), ingest/stats.py (xG/possession persistence) (+2 more)

### Community 17 - "Dashboard Web App"
Cohesion: 0.39
Nodes (7): HTMLResponse, Request, index(), _leagues(), models(), predictions(), Read-only ops dashboard for football-predictor.  GET-only, zero mutation — reads

### Community 18 - "Prediction Tracker"
Cohesion: 0.28
Nodes (6): _dec4(), PredictionTracker, Decimal, Record pre-match predictions, guarding against duplicates.  Example:     >>> tra, Persist model predictions, one per (match, model).      The DB carries a ``UNIQU, Insert a prediction. Returns its id, or None if a duplicate was skipped.

### Community 19 - "Prediction Validator"
Cohesion: 0.25
Nodes (5): main(), Validate predictions for finished matches. Run ~2h after kickoff via cron.  Usag, PredictionValidator, Validate predictions against real results post-match.  Example:     >>> Predicti, Score every unvalidated prediction whose match has finished.

### Community 20 - "Odds Ingestion"
Cohesion: 0.36
Nodes (7): _dec3(), fetch_odds(), _fetch_with_fallback(), Decimal, Fetch 1X2 odds and store them, provider-agnostic with primary/fallback.  Consume, Try the configured primary odds provider, then the fallback, if any., Fetch and store all 1X2 odds for a fixture.      Args:         api_fixture_id: T

### Community 21 - "Model Registry Concepts"
Cohesion: 0.33
Nodes (5): predict_ensemble() (ml/predict.py), MODEL_REGISTRY (ml/train.py), Multi-algorithm training (MODEL_REGISTRY: baseline/xgboost/random_forest), main(), Fetch 1X2 odds for scheduled matches using the configured provider chain.  Usage

### Community 22 - "Advanced Stats Ingestion"
Cohesion: 0.47
Nodes (5): _dec2(), fetch_stats(), Decimal, Fetch and persist advanced stats (xG, possession) onto ``matches``.  Separate fr, Fetch advanced stats for a fixture and write them onto its ``matches`` row.

## Knowledge Gaps
- **14 isolated node(s):** `footy`, `htmx.org@1.9.12 CDN script include`, `MODEL_REGISTRY (ml/train.py)`, `predict_ensemble() (ml/predict.py)`, `FixtureDTO (ingest/schemas.py)` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_settings()` connect `Config & Training CLI` to `Provider Ingestion Protocol`, `The Odds API Provider`, `Ensemble Prediction`, `API-Football Client`, `ORM & Backtest Script`, `Database Engine Setup`, `Odds Ingestion`, `Advanced Stats Ingestion`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Why does `train_model()` connect `Multi-Algorithm Training` to `Feature Engineering`, `Ensemble Prediction`, `Config & Training CLI`, `Data Loading & Scripts`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Why does `build_settled_bets()` connect `ORM & Backtest Script` to `Database Engine Setup`, `Backtest Engine`, `Config & Training CLI`, `Value Betting`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `OddsQuery` (e.g. with `ApiFootballProvider` and `Provider`) actually correct?**
  _`OddsQuery` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `session_scope()` (e.g. with `main()` and `main()`) actually correct?**
  _`session_scope()` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SportmonksProvider` (e.g. with `ProviderError` and `UnsupportedProviderMixin`) actually correct?**
  _`SportmonksProvider` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `get_settings()` (e.g. with `build_settled_bets()` and `main()`) actually correct?**
  _`get_settings()` has 12 INFERRED edges - model-reasoned connections that need verification._