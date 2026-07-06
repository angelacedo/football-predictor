"""One-off: train a World Cup-specific model on FIFA ranking + host-nation
features (not club-football's rolling form - see footy.ml.features_worldcup's
docstring for why). Not on the weekly cron: World Cup data only grows every
4 years, so this is run manually, rarely - same shape as
scripts/backfill_f1_historical.py.

Backfills 2010/2014/2018/2022 fixtures via the same sync_league() already
used for the live 2026 sync - no new provider code. 2026 itself is NOT
backfilled here since football_sync_predict already syncs it daily.

Usage:
    python scripts/train_world_cup.py
"""

from __future__ import annotations

import logging

from footy.data import matches_dataframe
from footy.ingest.matches import sync_league
from footy.ml.features_worldcup import (
    FEATURE_COLUMNS_WORLDCUP,
    compute_feature_frame_worldcup,
    load_rankings,
)
from footy.ml.registry import save_model
from footy.ml.train import MODEL_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.train_world_cup")

WORLD_CUP_LEAGUE_ID = 1
BACKFILL_SEASONS = (2010, 2014, 2018, 2022)
ARTIFACT_NAME = "baseline_World_Cup"
ALGORITHM = "baseline"


def main() -> None:
    for season in BACKFILL_SEASONS:
        n = sync_league(WORLD_CUP_LEAGUE_ID, season)
        log.info("Backfilled %d World Cup fixture(s) for %d", n, season)

    df = matches_dataframe("World Cup")
    rankings = load_rankings()
    feats = compute_feature_frame_worldcup(df, rankings)
    played = feats[feats["result"].notna()]
    if played.empty:
        raise SystemExit("No finished World Cup matches to train on.")

    x = played[list(FEATURE_COLUMNS_WORLDCUP)]
    y = played["result"].astype(str)
    pipe = MODEL_REGISTRY[ALGORITHM]()
    pipe.fit(x, y)
    artifact = save_model(pipe, ARTIFACT_NAME)
    log.info("Trained '%s' on %d World Cup matches -> %s", ARTIFACT_NAME, len(played), artifact)


if __name__ == "__main__":
    main()
