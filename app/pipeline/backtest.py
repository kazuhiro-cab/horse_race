from __future__ import annotations

import csv
from pathlib import Path

from app import db
from app.config import LOG_DIR


def run_backtest(from_date: str, to_date: str, market: str = "all") -> dict:
    db.init_db()
    with db.connect() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM bankroll_log WHERE logged_at >= ? AND logged_at <= ?", (from_date, to_date)).fetchall()]
    if market.lower() != "all":
        rows = [r for r in rows if r["market"] == market.upper()]
    total_bet = sum(r["bet_amount"] for r in rows)
    total_payout = sum(r["payout"] or 0 for r in rows)
    hit = sum(1 for r in rows if r["result"] == "WIN")
    n = len(rows)
    stats = {
        "hit_rate": hit / n if n else 0.0,
        "recovery_rate": total_payout / total_bet if total_bet else 0.0,
        "ev_calibration_error": 0.0,
        "favorite_trust_accuracy": 0.0,
        "risk_score_accuracy": 0.0,
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    curve = Path(LOG_DIR / "bankroll_curve.csv")
    bankroll = 10000.0
    with curve.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "bankroll"])
        for i, r in enumerate(rows, start=1):
            bankroll -= r["bet_amount"]
            bankroll += r["payout"] or 0
            w.writerow([i, bankroll])
    stats["bankroll_curve_csv"] = str(curve)
    return stats
