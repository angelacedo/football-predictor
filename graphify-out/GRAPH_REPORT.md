# Graph Report - .  (2026-07-05)

## Corpus Check
- Corpus is ~13,448 words - fits in a single context window. You may not need a graph.

## Summary
- 495 nodes · 861 edges · 36 communities (34 shown, 2 thin omitted)
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 176 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Domain Vocabulary & Ensemble Prediction|Domain Vocabulary & Ensemble Prediction]]
- [[_COMMUNITY_Backtest Engine Script|Backtest Engine Script]]
- [[_COMMUNITY_Prediction Metrics|Prediction Metrics]]
- [[_COMMUNITY_Sportmonks Provider|Sportmonks Provider]]
- [[_COMMUNITY_Multi-Algorithm Training|Multi-Algorithm Training]]
- [[_COMMUNITY_Value Betting|Value Betting]]
- [[_COMMUNITY_The Odds API Provider|The Odds API Provider]]
- [[_COMMUNITY_Backtest Engine|Backtest Engine]]
- [[_COMMUNITY_Feature Engineering|Feature Engineering]]
- [[_COMMUNITY_Deployment & Web Templates|Deployment & Web Templates]]
- [[_COMMUNITY_Provider Error Handling|Provider Error Handling]]
- [[_COMMUNITY_Staking Strategy|Staking Strategy]]
- [[_COMMUNITY_Fixture Sync|Fixture Sync]]
- [[_COMMUNITY_Bankroll Management|Bankroll Management]]
- [[_COMMUNITY_API-Football Provider + Tests|API-Football Provider + Tests]]
- [[_COMMUNITY_ORM Models|ORM Models]]
- [[_COMMUNITY_Database Engine Setup|Database Engine Setup]]
- [[_COMMUNITY_Dashboard Web App|Dashboard Web App]]
- [[_COMMUNITY_Ingestion DTOs & Schemas|Ingestion DTOs & Schemas]]
- [[_COMMUNITY_Data Loading & Scripts|Data Loading & Scripts]]
- [[_COMMUNITY_Provider Ingestion Protocol|Provider Ingestion Protocol]]
- [[_COMMUNITY_API-Football Client Logic|API-Football Client Logic]]
- [[_COMMUNITY_Model Registry Concepts|Model Registry Concepts]]
- [[_COMMUNITY_Prediction Validator|Prediction Validator]]
- [[_COMMUNITY_Odds Ingestion|Odds Ingestion]]
- [[_COMMUNITY_Base Provider Utilities|Base Provider Utilities]]
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
7. `MatchProbs` - 14 edges
8. `ProviderError` - 14 edges
9. `Provider` - 14 edges
10. `FixtureDTO` - 14 edges

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
- **Production docker-compose stack (db, app, web) behind Traefik** — docker_compose_prod_db, docker_compose_prod_app, docker_compose_prod_web [EXTRACTED 1.00]
- **Local docker-compose stack (db, app, web)** — docker_compose_db, docker_compose_app, docker_compose_web [EXTRACTED 1.00]
- **Jinja2 template inheritance from base.html** — web_templates_base_base, web_templates_index_index, web_templates_models_models, web_templates_predictions_predictions [EXTRACTED 1.00]

## Communities (36 total, 2 thin omitted)

### Community 0 - "Domain Vocabulary & Ensemble Prediction"
Cohesion: 0.07
Nodes (41): DummyClassifier, main(), MatchProbs, Shared 1X2 domain vocabulary - no ML/DB/ingest dependencies.  Moved out of ml/ s, Calibrated 1X2 probabilities for a single match., Return probabilities in (HOME, DRAW, AWAY) order., Confidence signal = the largest class probability., predict_ensemble() (+33 more)

### Community 1 - "Backtest Engine Script"
Cohesion: 0.05
Nodes (33): BaseSettings, CaptureFixture, build_settled_bets(), main(), _odds_for(), Paper backtest: turn validated predictions + odds into value bets and score them, Return (any pre-match odds, closing odds) rows for a match., main() (+25 more)

### Community 2 - "Prediction Metrics"
Cohesion: 0.07
Nodes (43): Probs, breakdown_by(), breakdown_by_league_and_model(), brier_score(), calibration_by_class(), log_loss_single(), mean_brier(), mean_log_loss() (+35 more)

### Community 3 - "Sportmonks Provider"
Cohesion: 0.07
Nodes (31): _fixture_from_json(), Any, Sportmonks provider adapter — fixtures + advanced stats (xG, possession).  Field, Fixtures + advanced stats via Sportmonks., SportmonksProvider, _stat_value(), _team_name(), Any (+23 more)

### Community 4 - "Multi-Algorithm Training"
Cohesion: 0.09
Nodes (28): BaseEstimator, ClassifierMixin, Pipeline, Series, build_pipeline(), build_random_forest_pipeline(), build_xgboost_pipeline(), _LabelEncodedXGBClassifier (+20 more)

### Community 5 - "Value Betting"
Cohesion: 0.14
Nodes (15): edge(), find_value_bet(), implied_probs(), Value detection: compare model probabilities to bookmaker odds.  A bet has posit, A selected value bet (paper only — never placed)., Expected value per unit staked minus 1: ``model_prob * odds - 1``., Overround-normalized market probabilities from 1X2 decimal odds., Return the highest-edge selection clearing ``threshold``, or None.      Args: (+7 more)

### Community 6 - "The Odds API Provider"
Cohesion: 0.20
Nodes (14): _matches_event(), _odds_from_event(), Any, The Odds API provider adapter — multi-bookmaker 1X2 odds.  Docs: https://the-odd, Multi-bookmaker 1X2 odds via The Odds API., TheOddsApiProvider, OddsQuery, Lookup key for odds.      Carries both the fixtures-provider's numeric id *and* (+6 more)

### Community 7 - "Backtest Engine"
Cohesion: 0.18
Nodes (14): backtest(), BacktestReport, Replay settled paper bets into performance stats.  Answers "do I actually have a, A resolved paper bet. ``closing_odds`` optional, enables CLV., Profit/loss: ``stake*(odds-1)`` on a win, ``-stake`` on a loss., Aggregate paper-betting performance., Compute ROI, hit-rate, max drawdown and CLV over ``bets``., SettledBet (+6 more)

### Community 8 - "Feature Engineering"
Cohesion: 0.18
Nodes (14): Map a final score to a 1X2 label., result_from_goals(), _avg(), compute_feature_frame(), DataFrame, Feature engineering for 1X2 prediction.  Features are **leakage-safe by construc, Compute leakage-safe features for every row in ``df``.      Args:         df: Ma, _matches() (+6 more)

### Community 9 - "Deployment & Web Templates"
Cohesion: 0.23
Nodes (15): build-push job (docker-publish.yml), web-build-push job (docker-publish.yml), app service (docker-compose.yml, builds locally), db service (docker-compose.yml, postgres), app service (docker-compose.prod.yml, prebuilt image), db service (docker-compose.prod.yml, postgres), web service (docker-compose.prod.yml, Traefik-routed), web service (docker-compose.yml, builds locally) (+7 more)

### Community 10 - "Provider Error Handling"
Cohesion: 0.22
Nodes (10): Exception, ProviderError, A provider call failed, or the provider doesn't support the capability., Default 'not supported by this provider' implementations.      Concrete adapters, UnsupportedProviderMixin, AdvancedStatsDTO, OddsDTO, Provider-agnostic DTOs.  ``matches.py``/``odds.py``/``stats.py`` consume only th (+2 more)

### Community 11 - "Staking Strategy"
Cohesion: 0.21
Nodes (12): flat_stake(), kelly_fraction(), kelly_stake(), Stake sizing. Paper only — computes amounts, never moves money.  Two methods:  *, Fixed fraction of bankroll (default 1%)., Fractional-Kelly bankroll fraction for a bet.      ``f* = (b*p - q) / b`` with `, Stake amount from fractional Kelly on ``bankroll``., Stake sizing: flat and fractional Kelly. (+4 more)

### Community 12 - "Fixture Sync"
Cohesion: 0.17
Nodes (10): main(), Sync fixtures/results for a league/season into ``matches``.  Usage:     python s, Upsert fixtures/results into ``matches``, provider-agnostic.  This module never, Insert new matches or update existing ones (keyed by ``api_fixture_id``).      R, Fetch all fixtures for a league/season and upsert them.      Args:         leagu, sync_league(), upsert_matches(), build_provider() (+2 more)

### Community 13 - "Bankroll Management"
Cohesion: 0.17
Nodes (6): Bankroll, Bankroll and risk limits for paper betting.  Caps a desired stake by (a) a per-b, Stateful paper bankroll with per-bet and per-group exposure caps., Return ``desired`` clamped by per-bet and remaining group-exposure caps., Reserve ``stake`` of open exposure for ``group``; returns the stake., Apply a settled bet: credit pnl and release the reserved exposure.

### Community 14 - "API-Football Provider + Tests"
Cohesion: 0.27
Nodes (8): ApiFootballProvider, Fixtures + odds via API-Football., FakeClient, Any, ApiFootballProvider: fixture/odds JSON -> DTOs, via a fake transport (no network, test_get_fixtures_maps_to_dto(), test_get_fixtures_unfinished_has_no_goals(), test_get_odds_extracts_match_winner_only()

### Community 15 - "ORM Models"
Cohesion: 0.24
Nodes (7): DeclarativeBase, Base, Bet, Match, Prediction, SQLAlchemy ORM models mirroring schema.sql.  The raw schema.sql remains the sour, Declarative base for all ORM models.

### Community 16 - "Database Engine Setup"
Cohesion: 0.22
Nodes (9): Engine, main(), Initialize the database by executing schema.sql.  Usage:     python scripts/init, Session, sessionmaker, get_engine(), Database engine and session factory.  Example:     >>> from footy.db import sess, Return the process-wide SQLAlchemy engine. (+1 more)

### Community 17 - "Dashboard Web App"
Cohesion: 0.33
Nodes (9): HTMLResponse, Request, Provide a transactional session scope; commits on success, rolls back on error., session_scope(), index(), _leagues(), models(), predictions() (+1 more)

### Community 18 - "Ingestion DTOs & Schemas"
Cohesion: 0.20
Nodes (10): config.py (provider config fields), Provider protocol (ingest/providers/base.py), provider registry _BUILDERS (ingest/providers/registry.py), AdvancedStatsDTO (ingest/schemas.py), FixtureDTO (ingest/schemas.py), OddsDTO (ingest/schemas.py), OddsQuery (ingest/schemas.py), ingest/stats.py (xG/possession persistence) (+2 more)

### Community 19 - "Data Loading & Scripts"
Cohesion: 0.24
Nodes (8): main(), Train the baseline model from matches in the DB.  Usage:     python scripts/trai, matches_dataframe(), DataFrame, Load DB rows into pandas frames for the ML layer., Return matches as a DataFrame with the columns the feature builder needs.      A, Return validated predictions joined to their match league/model, for metrics., validated_predictions_dataframe()

### Community 20 - "Provider Ingestion Protocol"
Cohesion: 0.22
Nodes (6): Protocol, Provider, Structural contract for a data-provider adapter., Return fixtures for a league/season., Return 1X2 odds (all bookmakers) for a fixture., Return xG/possession for a fixture, or None if unavailable.

### Community 21 - "API-Football Client Logic"
Cohesion: 0.28
Nodes (6): _fixture_from_json(), _match_winner_odds(), Any, API-Football (v3) provider adapter — fixtures + odds.  Wraps the existing :class, FixtureDTO, A single fixture, normalized across providers.

### Community 22 - "Model Registry Concepts"
Cohesion: 0.25
Nodes (6): predict_ensemble() (ml/predict.py), MODEL_REGISTRY (ml/train.py), Multi-algorithm training (MODEL_REGISTRY: baseline/xgboost/random_forest), main(), Fetch 1X2 odds for scheduled matches using the configured provider chain.  Usage, Predict all SCHEDULED matches and record the predictions.  Idempotent: re-runnin

### Community 23 - "Prediction Validator"
Cohesion: 0.25
Nodes (5): main(), Validate predictions for finished matches. Run ~2h after kickoff via cron.  Usag, PredictionValidator, Validate predictions against real results post-match.  Example:     >>> Predicti, Score every unvalidated prediction whose match has finished.

### Community 24 - "Odds Ingestion"
Cohesion: 0.36
Nodes (7): _dec3(), fetch_odds(), _fetch_with_fallback(), Decimal, Fetch 1X2 odds and store them, provider-agnostic with primary/fallback.  Consume, Try the configured primary odds provider, then the fallback, if any., Fetch and store all 1X2 odds for a fixture.      Args:         api_fixture_id: T

### Community 25 - "Base Provider Utilities"
Cohesion: 0.40
Nodes (5): datetime, Common contract every data provider adapter satisfies.  A provider does not have, Normalize a datetime to naive UTC for cross-provider comparison.      ``matches., to_naive_utc(), test_odds_unsupported()

### Community 26 - "Advanced Stats Ingestion"
Cohesion: 0.47
Nodes (5): _dec2(), fetch_stats(), Decimal, Fetch and persist advanced stats (xG, possession) onto ``matches``.  Separate fr, Fetch advanced stats for a fixture and write them onto its ``matches`` row.

## Knowledge Gaps
- **14 isolated node(s):** `footy`, `MODEL_REGISTRY (ml/train.py)`, `predict_ensemble() (ml/predict.py)`, `FixtureDTO (ingest/schemas.py)`, `OddsDTO (ingest/schemas.py)` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `train_model()` connect `Multi-Algorithm Training` to `Feature Engineering`, `Backtest Engine Script`, `Data Loading & Scripts`, `Domain Vocabulary & Ensemble Prediction`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `Backtest Engine Script` to `Domain Vocabulary & Ensemble Prediction`, `Sportmonks Provider`, `Fixture Sync`, `Database Engine Setup`, `Odds Ingestion`, `Advanced Stats Ingestion`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `build_settled_bets()` connect `Backtest Engine Script` to `Domain Vocabulary & Ensemble Prediction`, `Value Betting`, `Backtest Engine`, `ORM Models`, `Dashboard Web App`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `OddsQuery` (e.g. with `ApiFootballProvider` and `Provider`) actually correct?**
  _`OddsQuery` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `session_scope()` (e.g. with `main()` and `main()`) actually correct?**
  _`session_scope()` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `SportmonksProvider` (e.g. with `ProviderError` and `UnsupportedProviderMixin`) actually correct?**
  _`SportmonksProvider` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `get_settings()` (e.g. with `build_settled_bets()` and `main()`) actually correct?**
  _`get_settings()` has 12 INFERRED edges - model-reasoned connections that need verification._