from __future__ import annotations

from datetime import datetime


def _weeks_between(d1: str, d2: str) -> float:
    return (datetime.fromisoformat(d2) - datetime.fromisoformat(d1)).days / 7.0


def build_features(race: dict, entries: list[dict], pp_map: dict[str, list[dict]]) -> list[dict]:
    feats = []
    for e in entries:
        pps = sorted(pp_map.get(e["horse_key"], []), key=lambda x: x.get("race_date", ""), reverse=True)
        last = pps[0] if pps else {}
        finish = float(last.get("finish_pos") or 10)
        distance = race.get("distance_m") or 0
        last_distance = last.get("distance_m") or distance
        rest_weeks = _weeks_between(last.get("race_date", race["date"]), race["date"]) if last else 4.0

        penalty = 1.0
        reasons: list[str] = []
        if distance - last_distance >= 400:
            penalty *= 0.85
            reasons.append("大幅距離延長")
        if last_distance - distance >= 400:
            penalty *= 0.85
            reasons.append("大幅距離短縮")
        if last and last.get("surface") and race.get("surface") and last.get("surface") != race.get("surface"):
            penalty *= 0.80
            reasons.append("馬場種別変更")
        if (e.get("horse_weight_diff") or 0) >= 8:
            penalty *= 0.90
            reasons.append("馬体重大幅変化")
        if (e.get("weight_carried") or 0) - (last.get("weight_carried") or e.get("weight_carried") or 0) >= 2:
            penalty *= 0.90
            reasons.append("大幅斤量増")
        if rest_weeks >= 12:
            penalty *= 0.88
            reasons.append("長期休養明け")
        if rest_weeks <= 2:
            penalty *= 0.92
            reasons.append("間隔詰め")

        feats.append(
            {
                "race_key": race["race_key"],
                "horse_key": e["horse_key"],
                "number": e["number"],
                "horse_name": e["horse_name"],
                "finish_proxy": finish,
                "distance_fit": 1.0 - min(abs(distance - last_distance) / 1200.0, 1.0),
                "weight_carried": e.get("weight_carried") or 55.0,
                "rest_weeks": rest_weeks,
                "risk_penalty": penalty,
                "risk_reasons": reasons,
            }
        )
    return feats
