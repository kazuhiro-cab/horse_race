from __future__ import annotations

import json
from datetime import datetime

from app import db
from app.config import DEFAULT_BANKROLL, DEFAULT_ODDS_MODE, LOG_DIR
from app.features.build import build_features
from app.i18n import market_to_ja, odds_mode_to_en
from app.markets.bets import build_ev_bets, ev_caution
from app.markets.probability import place_probabilities, trifecta_probabilities, trio_probabilities
from app.model.calibration import PlattCalibrator
from app.model.simple_ranker import SimpleRanker
from app.pipeline.fetch import snapshot_odds


def _pair_probs(win_probs: dict[int, float]) -> dict[str, float]:
    horses = list(win_probs)
    pairs = {}
    for i in range(len(horses)):
        for j in range(i + 1, len(horses)):
            a, b = horses[i], horses[j]
            p = win_probs[a] * (win_probs[b] / max(1 - win_probs[a], 1e-9)) + win_probs[b] * (win_probs[a] / max(1 - win_probs[b], 1e-9))
            pairs[f"{min(a,b)}-{max(a,b)}"] = min(p, 1.0)
    return pairs




def _ordered_pair_probs(win_probs: dict[int, float]) -> dict[str, float]:
    horses=list(win_probs)
    out={}
    for a in horses:
        for b in horses:
            if a==b:
                continue
            out[f"{a}-{b}"]=win_probs[a]*(win_probs[b]/max(1-win_probs[a],1e-9))
    return out

def predict_race(race_key: str, odds_mode: str = DEFAULT_ODDS_MODE, bankroll: float = DEFAULT_BANKROLL) -> dict:
    db.init_db()
    mode_en = odds_mode_to_en(odds_mode) if odds_mode in ("前日最終", "前日発売開始直後", "当日発売開始直後") else odds_mode
    races = [r for r in db.fetch_races() if r["race_key"] == race_key]
    if not races:
        raise ValueError(f"race not found: {race_key}")
    race = races[0]
    entries = db.fetch_entries(race_key)

    pp_map = {}
    with db.connect() as con:
        for e in entries:
            rows = con.execute("SELECT * FROM past_performances WHERE horse_key = ?", (e["horse_key"],)).fetchall()
            pp_map[e["horse_key"]] = [dict(r) for r in rows]

    feats = build_features(race, entries, pp_map)
    pred = SimpleRanker().predict_win_probs(feats)
    calibrated = PlattCalibrator(1.0, 0.0).transform_many([p["win_prob"] for p in pred])
    win_probs = {p["number"]: cp for p, cp in zip(pred, calibrated)}

    place_probs = {str(k): v for k, v in place_probabilities(win_probs).items()}
    pair_probs = _pair_probs(win_probs)
    ordered_pair_probs = _ordered_pair_probs(win_probs)
    trio_probs = trio_probabilities(win_probs)
    trifecta_probs = trifecta_probabilities(win_probs)
    win_prob_map = {str(k): v for k, v in win_probs.items()}

    market_prob_map = {
        "単勝": win_prob_map,
        "複勝": place_probs,
        "枠連": pair_probs,
        "馬連": pair_probs,
        "馬単": ordered_pair_probs,
        "ワイド": pair_probs,
        "三連複": trio_probs,
        "三連単": trifecta_probs,
        "WIN5": {},
    }

    needed = list(market_prob_map.keys())
    snapshots = {}
    for m in needed:
        snap = db.fetch_latest_odds(race_key, mode_en, m)
        if not snap:
            snapshot_odds(race["date"], mode=mode_en, org=race["org"])
            snap = db.fetch_latest_odds(race_key, mode_en, m)
        snapshots[m] = snap

    bets = {}
    for m, probs in market_prob_map.items():
        snap = snapshots.get(m)
        if not snap or not probs:
            bets[m] = []
            continue
        bets[m] = build_ev_bets(probs, snap["payload"], bankroll)

    captured_at = next((v["captured_at"] for v in snapshots.values() if v), datetime.now().isoformat(timespec="seconds"))
    predicted_at = datetime.now().isoformat(timespec="seconds")
    payload = {
        "race": race,
        "features": feats,
        "favorite_trust": {"score": pred[0].get("favorite_trust_score", 1.0), "reasons": pred[0].get("favorite_trust_reasons", [])},
        "win_probs": win_probs,
        "bets": bets,
        "caution": ev_caution(captured_at),
        "notes": "WIN5はJRAのみ・対象レース限定",
    }

    for market, rows in bets.items():
        db.insert_prediction(race_key, predicted_at, captured_at, market, {"bets": rows})
        for b in rows:
            db.insert_bankroll_log(
                {
                    "logged_at": predicted_at,
                    "race_key": race_key,
                    "market": market,
                    "combination": b["combination"],
                    "bet_amount": b["bet_amount"],
                    "odds": b["odds"],
                    "result": "未確定",
                    "payout": None,
                    "bankroll_after": bankroll - b["bet_amount"],
                }
            )

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{race_key}.json"
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["log_path"] = str(log_path)
    return payload
