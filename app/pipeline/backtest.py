from __future__ import annotations

import csv
from pathlib import Path

from app import db
from app.config import LOG_DIR
from app.pipeline.result import settle_pending_results


def _normalize_backtest_range(from_date: str, to_date: str) -> tuple[str, str]:
    start = from_date if "T" in from_date else f"{from_date}T00:00:00"
    end = to_date if "T" in to_date else f"{to_date}T23:59:59"
    return start, end


def run_backtest(from_date: str, to_date: str, market: str = "全券種", progress_callback=None) -> dict:
    db.init_db()
    if progress_callback:
        progress_callback("バックテスト実行中...（結果取得中）")
    settle_pending_results(progress_callback=progress_callback)
    start, end = _normalize_backtest_range(from_date, to_date)
    with db.connect() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM bankroll_log WHERE logged_at >= ? AND logged_at <= ?", (start, end)).fetchall()]

    if market not in ("all", "全券種"):
        rows = [r for r in rows if r["market"] == market]

    total_bet = sum(r["bet_amount"] for r in rows)
    total_payout = sum((r["payout"] or 0) for r in rows)
    hit = sum(1 for r in rows if r["result"] == "的中")
    n = len(rows)
    stats = {
        "的中率": hit / n if n else 0.0,
        "回収率": total_payout / total_bet if total_bet else 0.0,
        "EV推定精度": 0.0,
        "1番人気信頼度スコア精度": 0.0,
        "凡走リスクスコア精度": 0.0,
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
            if progress_callback:
                progress_callback(f"バックテスト実行中...（{i}/{n}）")

    stats["資金推移CSV"] = str(curve)
    return stats
