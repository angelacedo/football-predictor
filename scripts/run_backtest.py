"""Paper backtest: turn validated predictions + odds into value bets and score them.

Level stakes (1 unit per value bet), so ROI == yield. No real bets are placed.

Usage:
    python scripts/run_backtest.py
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from footy.betting.backtest import SettledBet, backtest
from footy.betting.value import find_value_bet
from footy.config import get_settings
from footy.db import session_scope
from footy.domain import RESULT_CLASSES, MatchProbs
from footy.orm import Match, Odds, Prediction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("footy.backtest")


def _odds_for(session, match_id: int) -> tuple[Odds | None, Odds | None]:
    """Return (any pre-match odds, closing odds) rows for a match."""
    rows = session.scalars(
        select(Odds).where(Odds.match_id == match_id).order_by(Odds.captured_at)
    ).all()
    if not rows:
        return None, None
    closing = next((o for o in rows if o.is_closing), None)
    return rows[0], closing


def build_settled_bets() -> list[SettledBet]:
    threshold = get_settings().edge_threshold
    bets: list[SettledBet] = []
    with session_scope() as session:
        stmt = (
            select(Prediction, Match)
            .join(Match, Prediction.match_id == Match.id)
            .where(Prediction.validated_at.is_not(None))
        )
        for pred, match in session.execute(stmt).all():
            pre, closing = _odds_for(session, match.id)
            if pre is None or match.actual_result is None:
                continue
            probs = MatchProbs(
                float(pred.prob_home_win), float(pred.prob_draw), float(pred.prob_away_win)
            )
            odds_tuple = (float(pre.odds_home), float(pre.odds_draw), float(pre.odds_away))
            bet = find_value_bet(probs, odds_tuple, threshold)
            if bet is None:
                continue
            idx = RESULT_CLASSES.index(bet.selection)
            closing_odds = (
                (float(closing.odds_home), float(closing.odds_draw), float(closing.odds_away))[idx]
                if closing is not None
                else None
            )
            bets.append(
                SettledBet(
                    selection=bet.selection,
                    odds=bet.market_odds,
                    stake=1.0,
                    won=bet.selection == match.actual_result,
                    closing_odds=closing_odds,
                )
            )
    return bets


def main() -> None:
    bets = build_settled_bets()
    report = backtest(bets)
    log.info("Backtest over %d value bets: %r", len(bets), report)
    print(report)


if __name__ == "__main__":
    main()
