from __future__ import annotations

from app.config import MAX_BET_RATIO_PER_RACE, MAX_BET_RATIO_PER_TICKET, MIN_BET_YEN


def kelly_half_fraction(ev: float, odds: float) -> float:
    if odds <= 1 or ev <= 1:
        return 0.0
    # ハーフケリーを使う理由: モデル推定誤差を考慮し、破産リスクを抑えるため。
    full = (ev - 1.0) / (odds - 1.0)
    half = max(full / 2.0, 0.0)
    return min(half, MAX_BET_RATIO_PER_TICKET)


def build_ev_bets(prob_map: dict[str, float], odds_map: dict[str, float], bankroll: float) -> list[dict]:
    bets = []
    for k, p in prob_map.items():
        odds = odds_map.get(k)
        if not odds:
            continue
        ev = p * odds
        if ev <= 1.0:
            continue
        ratio = kelly_half_fraction(ev, odds)
        amount = int(bankroll * ratio // 100 * 100)
        if amount < MIN_BET_YEN:
            continue
        bets.append({"combination": k, "prob": p, "odds": odds, "ev": ev, "bet_amount": amount})

    bets.sort(key=lambda x: x["ev"], reverse=True)
    cap = bankroll * MAX_BET_RATIO_PER_RACE
    total = 0
    capped = []
    for b in bets:
        if total >= cap:
            break
        remain = int((cap - total) // 100 * 100)
        if remain < MIN_BET_YEN:
            break
        if b["bet_amount"] > remain:
            b["bet_amount"] = remain
        total += b["bet_amount"]
        capped.append(b)
    return capped


def ev_caution(captured_at: str) -> str:
    return (
        f"[注意] このEVは {captured_at} 時点のオッズを基準にした評価値です。\n"
        "       当日のオッズは変動するため、実際のEVは異なります。\n"
        "       EV > 1.0 は長期的な期待値の優位性を示すものであり、\n"
        "       個別レースの的中を保証するものではありません。"
    )
