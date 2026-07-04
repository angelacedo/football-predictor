# Graph Report - /Users/angel/Desktop/Apps/Python/football-predictor  (2026-07-04)

## Corpus Check
- Corpus is ~6,283 words - fits in a single context window. You may not need a graph.

## Summary
- 258 nodes · 394 edges · 21 communities (20 shown, 1 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 84 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Value Bet Detection|Value Bet Detection]]
- [[_COMMUNITY_CLI Scripts (Entry Points)|CLI Scripts (Entry Points)]]
- [[_COMMUNITY_Backtest Orchestration + ORM Base|Backtest Orchestration + ORM Base]]
- [[_COMMUNITY_Aggregate Metrics|Aggregate Metrics]]
- [[_COMMUNITY_Prediction Scoring (BrierLogLoss)|Prediction Scoring (Brier/LogLoss)]]
- [[_COMMUNITY_Paper Betting Backtest|Paper Betting Backtest]]
- [[_COMMUNITY_Model Registry + Training|Model Registry + Training]]
- [[_COMMUNITY_Config + API Client|Config + API Client]]
- [[_COMMUNITY_Feature Engineering|Feature Engineering]]
- [[_COMMUNITY_Staking (KellyFlat)|Staking (Kelly/Flat)]]
- [[_COMMUNITY_Bankroll Risk Limits|Bankroll Risk Limits]]
- [[_COMMUNITY_Match Ingestion|Match Ingestion]]
- [[_COMMUNITY_Odds Ingestion|Odds Ingestion]]
- [[_COMMUNITY_Prediction Tracker|Prediction Tracker]]
- [[_COMMUNITY_Package Root (footy)|Package Root (footy)]]

## God Nodes (most connected - your core abstractions)
1. `MatchProbs` - 14 edges
2. `session_scope()` - 13 edges
3. `build_settled_bets()` - 10 edges
4. `backtest()` - 10 edges
5. `compute_feature_frame()` - 10 edges
6. `SettledBet` - 9 edges
7. `find_value_bet()` - 9 edges
8. `fetch_odds()` - 9 edges
9. `predict_match()` - 9 edges
10. `Match` - 9 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `ApiFootball`  [INFERRED]
  scripts/fetch_odds.py → src/footy/ingest/client.py
- `main()` --calls--> `fetch_odds()`  [INFERRED]
  scripts/fetch_odds.py → src/footy/ingest/odds.py
- `main()` --calls--> `get_engine()`  [INFERRED]
  scripts/init_db.py → src/footy/db.py
- `main()` --calls--> `predict_match()`  [INFERRED]
  scripts/predict_upcoming.py → src/footy/ml/predict.py
- `main()` --calls--> `load_latest()`  [INFERRED]
  scripts/predict_upcoming.py → src/footy/ml/registry.py

## Import Cycles
- None detected.

## Communities (21 total, 1 thin omitted)

### Community 0 - "Value Bet Detection"
Cohesion: 0.09
Nodes (25): edge(), find_value_bet(), implied_probs(), Value detection: compare model probabilities to bookmaker odds.  A bet has posit, A selected value bet (paper only — never placed)., Expected value per unit staked minus 1: ``model_prob * odds - 1``., Overround-normalized market probabilities from 1X2 decimal odds., Return the highest-edge selection clearing ``threshold``, or None.      Args: (+17 more)

### Community 1 - "CLI Scripts (Entry Points)"
Cohesion: 0.10
Nodes (23): Engine, main(), Fetch 1X2 odds for scheduled matches.  Usage:     python scripts/fetch_odds.py, main(), Initialize the database by executing schema.sql.  Usage:     python scripts/init, main(), Predict all SCHEDULED matches and record the predictions.  Idempotent: re-runnin, main() (+15 more)

### Community 2 - "Backtest Orchestration + ORM Base"
Cohesion: 0.11
Nodes (18): DeclarativeBase, build_settled_bets(), main(), _odds_for(), Paper backtest: turn validated predictions + odds into value bets and score them, Return (any pre-match odds, closing odds) rows for a match., main(), Validate predictions for finished matches. Run ~2h after kickoff via cron.  Usag (+10 more)

### Community 3 - "Aggregate Metrics"
Cohesion: 0.13
Nodes (23): breakdown_by(), calibration_by_class(), mean_brier(), mean_log_loss(), _onehot(), overall_accuracy(), DataFrame, _raise() (+15 more)

### Community 4 - "Prediction Scoring (Brier/LogLoss)"
Cohesion: 0.16
Nodes (16): Probs, brier_score(), log_loss_single(), predicted_result(), Multiclass Brier score: ``sum((p_i - y_i)**2)`` over HOME/DRAW/AWAY.      Range, Log loss for one prediction: ``-log(clip(p_actual))``.      With a one-hot targe, Return the argmax 1X2 label for a probability vector., Validate all pending predictions for finished matches.          For each: comput (+8 more)

### Community 5 - "Paper Betting Backtest"
Cohesion: 0.18
Nodes (14): backtest(), BacktestReport, Replay settled paper bets into performance stats.  Answers "do I actually have a, A resolved paper bet. ``closing_odds`` optional, enables CLV., Profit/loss: ``stake*(odds-1)`` on a win, ``-stake`` on a loss., Aggregate paper-betting performance., Compute ROI, hit-rate, max drawdown and CLV over ``bets``., SettledBet (+6 more)

### Community 6 - "Model Registry + Training"
Cohesion: 0.16
Nodes (15): Path, Pipeline, _dir(), load_latest(), Any, Model artifact storage and versioning (joblib).  Artifacts are named ``<model_na, Persist ``model`` under a timestamped name and update the ``_latest`` pointer., Load the current version of ``model_name``.      Raises:         FileNotFoundErr (+7 more)

### Community 7 - "Config + API Client"
Cohesion: 0.14
Nodes (11): BaseSettings, get_settings(), Application settings loaded from environment / .env.  Example:     >>> from foot, Typed application configuration.      Attributes:         football_api_key: API-, Return the process-wide cached settings instance., Settings, ApiFootball, Any (+3 more)

### Community 8 - "Feature Engineering"
Cohesion: 0.19
Nodes (14): _avg(), compute_feature_frame(), DataFrame, Feature engineering for 1X2 prediction.  Features are **leakage-safe by construc, Map a final score to a 1X2 label., Compute leakage-safe features for every row in ``df``.      Args:         df: Ma, result_from_goals(), _matches() (+6 more)

### Community 9 - "Staking (Kelly/Flat)"
Cohesion: 0.21
Nodes (12): flat_stake(), kelly_fraction(), kelly_stake(), Stake sizing. Paper only — computes amounts, never moves money.  Two methods:  *, Fixed fraction of bankroll (default 1%)., Fractional-Kelly bankroll fraction for a bet.      ``f* = (b*p - q) / b`` with `, Stake amount from fractional Kelly on ``bankroll``., Stake sizing: flat and fractional Kelly. (+4 more)

### Community 10 - "Bankroll Risk Limits"
Cohesion: 0.17
Nodes (6): Bankroll, Bankroll and risk limits for paper betting.  Caps a desired stake by (a) a per-b, Stateful paper bankroll with per-bet and per-group exposure caps., Return ``desired`` clamped by per-bet and remaining group-exposure caps., Reserve ``stake`` of open exposure for ``group``; returns the stake., Apply a settled bet: credit pnl and release the reserved exposure.

### Community 11 - "Match Ingestion"
Cohesion: 0.31
Nodes (8): parse_fixture(), Any, Fetch fixtures/results from API-Football and upsert into ``matches``.  Example:, Map an API-Football fixture object to ``matches`` column values., Insert new matches or update existing ones (keyed by ``api_fixture_id``).      R, Fetch all fixtures for a league/season and upsert them., sync_league(), upsert_matches()

### Community 12 - "Odds Ingestion"
Cohesion: 0.31
Nodes (8): _dec3(), fetch_odds(), parse_match_winner(), Any, Decimal, Fetch 1X2 (Match Winner) odds from API-Football and store them.  Example:     >>, Extract (home, draw, away) decimal odds from a bookmaker object, or None., Fetch and store all Match-Winner odds for a fixture.      Returns:         Numbe

### Community 13 - "Prediction Tracker"
Cohesion: 0.28
Nodes (6): _dec4(), PredictionTracker, Decimal, Record pre-match predictions, guarding against duplicates.  Example:     >>> tra, Persist model predictions, one per (match, model).      The DB carries a ``UNIQU, Insert a prediction. Returns its id, or None if a duplicate was skipped.

## Knowledge Gaps
- **1 isolated node(s):** `footy`
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_settled_bets()` connect `Backtest Orchestration + ORM Base` to `Value Bet Detection`, `CLI Scripts (Entry Points)`, `Paper Betting Backtest`, `Config + API Client`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `session_scope()` connect `CLI Scripts (Entry Points)` to `Backtest Orchestration + ORM Base`, `Prediction Scoring (Brier/LogLoss)`, `Match Ingestion`, `Odds Ingestion`, `Prediction Tracker`?**
  _High betweenness centrality (0.178) - this node is a cross-community bridge._
- **Why does `MatchProbs` connect `Value Bet Detection` to `Backtest Orchestration + ORM Base`, `Prediction Tracker`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `MatchProbs` (e.g. with `build_settled_bets()` and `ValueBet`) actually correct?**
  _`MatchProbs` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `session_scope()` (e.g. with `main()` and `main()`) actually correct?**
  _`session_scope()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `build_settled_bets()` (e.g. with `find_value_bet()` and `get_settings()`) actually correct?**
  _`build_settled_bets()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `backtest()` (e.g. with `main()` and `test_clv()`) actually correct?**
  _`backtest()` has 6 INFERRED edges - model-reasoned connections that need verification._