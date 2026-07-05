-- Football betting bot schema. Paper/backtest only — no real-money execution.
-- Run with: psql "$DATABASE_URL" -f schema.sql  (or scripts/init_db.py)

CREATE TABLE IF NOT EXISTS matches (
    id             SERIAL PRIMARY KEY,
    api_fixture_id INTEGER UNIQUE NOT NULL,
    league         VARCHAR(80)  NOT NULL,
    season         INTEGER      NOT NULL,
    home_team      VARCHAR(80)  NOT NULL,
    away_team      VARCHAR(80)  NOT NULL,
    kickoff        TIMESTAMP    NOT NULL,
    status         VARCHAR(10)  NOT NULL DEFAULT 'SCHEDULED',  -- SCHEDULED | FINISHED
    home_goals     INTEGER,
    away_goals     INTEGER,
    xg_home         DECIMAL(5, 2),  -- expected goals, from a stats provider
    xg_away         DECIMAL(5, 2),
    possession_home DECIMAL(5, 2),  -- percent, 0-100
    possession_away DECIMAL(5, 2)
);
CREATE INDEX IF NOT EXISTS idx_matches_status  ON matches (status);
CREATE INDEX IF NOT EXISTS idx_matches_kickoff ON matches (kickoff);

-- Idempotent migration for pre-existing databases (fresh installs already get
-- these via CREATE TABLE above; IF NOT EXISTS makes re-running this file safe).
ALTER TABLE matches ADD COLUMN IF NOT EXISTS xg_home DECIMAL(5, 2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS xg_away DECIMAL(5, 2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS possession_home DECIMAL(5, 2);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS possession_away DECIMAL(5, 2);

CREATE TABLE IF NOT EXISTS predictions (
    id                 SERIAL PRIMARY KEY,
    match_id           INTEGER NOT NULL REFERENCES matches (id),
    model_name         VARCHAR(50) NOT NULL,
    prediction_date    TIMESTAMP   NOT NULL DEFAULT now(),
    prob_home_win      DECIMAL(5, 4) NOT NULL,
    prob_draw          DECIMAL(5, 4) NOT NULL,
    prob_away_win      DECIMAL(5, 4) NOT NULL,
    predicted_score_home INTEGER,
    predicted_score_away INTEGER,
    confidence_score   DECIMAL(5, 4),

    -- Filled post-match by the validator.
    actual_score_home  INTEGER,
    actual_score_away  INTEGER,
    actual_result      VARCHAR(10),               -- HOME | DRAW | AWAY
    brier_score        DECIMAL(10, 6),
    log_loss           DECIMAL(10, 6),
    is_correct         BOOLEAN,
    validated_at       TIMESTAMP,

    UNIQUE (match_id, model_name)                  -- one prediction per model per match
);
CREATE INDEX IF NOT EXISTS idx_predictions_unvalidated
    ON predictions (validated_at) WHERE validated_at IS NULL;

CREATE TABLE IF NOT EXISTS odds (
    id          SERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches (id),
    bookmaker   VARCHAR(60) NOT NULL,
    odds_home   DECIMAL(7, 3) NOT NULL,
    odds_draw   DECIMAL(7, 3) NOT NULL,
    odds_away   DECIMAL(7, 3) NOT NULL,
    captured_at TIMESTAMP NOT NULL DEFAULT now(),
    is_closing  BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_odds_match ON odds (match_id);

-- Paper bets. stake/pnl are backtest units, NOT currency moved. No execution.
CREATE TABLE IF NOT EXISTS bets (
    id             SERIAL PRIMARY KEY,
    prediction_id  INTEGER NOT NULL REFERENCES predictions (id),
    odds_id        INTEGER NOT NULL REFERENCES odds (id),
    selection      VARCHAR(10) NOT NULL,          -- HOME | DRAW | AWAY
    model_prob     DECIMAL(5, 4) NOT NULL,
    market_odds    DECIMAL(7, 3) NOT NULL,
    edge           DECIMAL(7, 4) NOT NULL,
    stake          DECIMAL(12, 4) NOT NULL,
    staking_method VARCHAR(20) NOT NULL,          -- flat | kelly
    status         VARCHAR(10) NOT NULL DEFAULT 'OPEN',  -- OPEN | WON | LOST
    pnl            DECIMAL(12, 4),
    placed_at      TIMESTAMP NOT NULL DEFAULT now(),
    settled_at     TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bets_status ON bets (status);

-- F1 module (src/sports/f1/) - own DeclarativeBase (F1Base), fully additive,
-- shares this same Postgres instance/DB but never joins the football tables
-- above. f1_-prefixed to avoid future name collisions with other sports.
CREATE TABLE IF NOT EXISTS f1_sessions (
    id                  SERIAL PRIMARY KEY,
    external_session_id INTEGER UNIQUE NOT NULL,
    season              INTEGER     NOT NULL,
    round               INTEGER     NOT NULL,
    circuit             VARCHAR(80) NOT NULL,
    session_type        VARCHAR(12) NOT NULL,  -- RACE | QUALIFYING | SPRINT
    start_time          TIMESTAMP   NOT NULL,
    status              VARCHAR(10) NOT NULL DEFAULT 'SCHEDULED'  -- SCHEDULED | FINISHED
);
CREATE INDEX IF NOT EXISTS idx_f1_sessions_status ON f1_sessions (status);

CREATE TABLE IF NOT EXISTS f1_entries (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES f1_sessions (id),
    driver_number   INTEGER     NOT NULL,
    driver_name     VARCHAR(80) NOT NULL,
    team            VARCHAR(80) NOT NULL,
    grid_position   INTEGER,      -- NULL: not reliably available via OpenF1, see adapter docstring
    finish_position INTEGER,
    status          VARCHAR(10) NOT NULL DEFAULT 'FINISHED',  -- FINISHED|DNF|DNS|DSQ
    points          DECIMAL(5, 2),

    UNIQUE (session_id, driver_number)
);

CREATE TABLE IF NOT EXISTS f1_predictions (
    id                 SERIAL PRIMARY KEY,
    session_id         INTEGER NOT NULL REFERENCES f1_sessions (id),
    driver_number      INTEGER     NOT NULL,
    model_name         VARCHAR(50) NOT NULL,
    prediction_date    TIMESTAMP   NOT NULL DEFAULT now(),
    predicted_position DECIMAL(6, 3) NOT NULL,

    -- Filled post-session by a future validator (mirrors predictions.validator's
    -- shape, but a ranking has no brier_score/log_loss - those need a one-hot
    -- HOME/DRAW/AWAY-style target, meaningless here).
    actual_position    INTEGER,
    mae_position       DECIMAL(6, 3),
    validated_at       TIMESTAMP,

    UNIQUE (session_id, driver_number, model_name)
);
CREATE INDEX IF NOT EXISTS idx_f1_predictions_unvalidated
    ON f1_predictions (validated_at) WHERE validated_at IS NULL;
