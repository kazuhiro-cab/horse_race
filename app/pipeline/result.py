from __future__ import annotations

import logging

from app import db
from app.sources.jra import JraSource
from app.sources.nar import NarSource


def _source_for_race(race_key: str):
    return JraSource() if race_key.startswith("JRA") else NarSource()


def _date_from_race_key(race_key: str) -> str | None:
    try:
        ymd = race_key.split("-")[1]
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    except Exception:
        return None


def _resolve_result(race_key: str, market: str, combination: str, odds: float | None) -> tuple[str, float | None]:
    src = _source_for_race(race_key)
    d = _date_from_race_key(race_key)
    if d:
        try:
            src.fetch_race_list(d, "JRA" if race_key.startswith("JRA") else "NAR")
        except Exception:
            logging.getLogger(__name__).exception("result prefetch failed for %s", race_key)
    payload = src.fetch_results(race_key)
    if not payload or payload.get("status") == "未確定":
        return "未確定", None

    payout_market = payload.get("payouts", {}).get(market, {})
    if combination in payout_market:
        return "的中", float(payout_market[combination])
    return "ハズレ", 0.0


def settle_pending_results(progress_callback=None) -> int:
    updated = 0
    with db.connect() as con:
        rows = [
            dict(r)
            for r in con.execute(
                "SELECT * FROM bankroll_log WHERE result = ? OR result IS NULL OR payout IS NULL",
                ("未確定",),
            ).fetchall()
        ]
    n = len(rows)
    for i, row in enumerate(rows, start=1):
        result, payout = _resolve_result(row["race_key"], row["market"], row["combination"], row.get("odds"))
        with db.connect() as con:
            con.execute("UPDATE bankroll_log SET result = ?, payout = ? WHERE id = ?", (result, payout, row["id"]))
        updated += 1
        if progress_callback:
            progress_callback(f"バックテスト実行中...（結果取得 {i}/{n}）")
    return updated
