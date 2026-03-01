from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app import db
from app.config import DEFAULT_BANKROLL, DEFAULT_ODDS_MODE, LOG_DIR
from app.features.build import build_features
from app.markets.bets import build_ev_bets, ev_caution
from app.markets.probability import place_probabilities, trifecta_probabilities, trio_probabilities
from app.model.calibration import PlattCalibrator
from app.model.simple_ranker import SimpleRanker
from app.pipeline.fetch import snapshot_odds


def predict_race(race_key: str, odds_mode: str = DEFAULT_ODDS_MODE, bankroll: float = DEFAULT_BANKROLL) -> dict:
    db.init_db()
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
    ranker = SimpleRanker()
    pred = ranker.predict_win_probs(feats)
    calibrator = PlattCalibrator(1.0, 0.0)
    calibrated = calibrator.transform_many([p["win_prob"] for p in pred])
    win_probs = {p["number"]: cp for p, cp in zip(pred, calibrated)}

    place_probs = {str(k): v for k, v in place_probabilities(win_probs).items()}
    trio_probs = trio_probabilities(win_probs)
    trifecta_probs = trifecta_probabilities(win_probs)

    latest_place = db.fetch_latest_odds(race_key, odds_mode, "PLACE")
    if not latest_place:
        snapshot_odds(race["date"], mode=odds_mode, org=race["org"])
        latest_place = db.fetch_latest_odds(race_key, odds_mode, "PLACE")
    latest_trio = db.fetch_latest_odds(race_key, odds_mode, "TRIO")
    latest_trifecta = db.fetch_latest_odds(race_key, odds_mode, "TRIFECTA")

    if not (latest_place and latest_trio and latest_trifecta):
        return {"race_key": race_key, "error": "[EV計算不可：オッズ未取得]"}

    place_bets = build_ev_bets(place_probs, latest_place["payload"], bankroll)
    trio_bets = build_ev_bets(trio_probs, latest_trio["payload"], bankroll)
    trifecta_bets = build_ev_bets(trifecta_probs, latest_trifecta["payload"], bankroll)

    predicted_at = datetime.now().isoformat(timespec="seconds")
    payload = {
        "race": race,
        "features": feats,
        "favorite_trust": {
            "score": pred[0].get("favorite_trust_score", 1.0),
            "reasons": pred[0].get("favorite_trust_reasons", []),
        },
        "win_probs": win_probs,
        "bets": {"PLACE": place_bets, "TRIO": trio_bets, "TRIFECTA": trifecta_bets},
        "caution": ev_caution(latest_place["captured_at"]),
    }

    for market, bets in payload["bets"].items():
        db.insert_prediction(race_key, predicted_at, latest_place["captured_at"], market, {"bets": bets})
        for b in bets:
            db.insert_bankroll_log(
                {
                    "logged_at": predicted_at,
                    "race_key": race_key,
                    "market": market,
                    "combination": b["combination"],
                    "bet_amount": b["bet_amount"],
                    "odds": b["odds"],
                    "result": "PENDING",
                    "payout": None,
                    "bankroll_after": bankroll - b["bet_amount"],
                }
            )

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{race_key}.json"
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["log_path"] = str(log_path)
    return payload
