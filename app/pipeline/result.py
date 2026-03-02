from __future__ import annotations

from app import db
from app.sources.jra import JraSource
from app.sources.nar import NarSource


def _resolve_result(race_key: str, market: str, combination: str, odds: float | None) -> tuple[str, float | None]:
    source = JraSource() if race_key.startswith("JRA") else NarSource()
    payload = source.fetch_results(race_key)
    if not payload or payload.get("status") == "未確定":
        return "未確定", None

    payout_market = payload.get("payouts", {}).get(market, {})
    if combination in payout_market:
        return "的中", float(payout_market[combination])
    return "ハズレ", 0.0


def settle_pending_results() -> int:
    updated = 0
    with db.connect() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM bankroll_log WHERE result = ?", ("未確定",)).fetchall()]
    for row in rows:
        result, payout = _resolve_result(row["race_key"], row["market"], row["combination"], row.get("odds"))
        with db.connect() as con:
            con.execute("UPDATE bankroll_log SET result = ?, payout = ? WHERE id = ?", (result, payout, row["id"]))
        updated += 1
    return updated
