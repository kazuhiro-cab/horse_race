from __future__ import annotations

import math

from app.model.base import BaseModel


class SimpleRanker(BaseModel):
    def __init__(self):
        self.coef = {
            "finish_proxy": -0.7,
            "distance_fit": 1.3,
            "weight_carried": -0.05,
            "rest_weeks": -0.03,
        }

    def _softmax(self, scores: list[float]) -> list[float]:
        m = max(scores)
        exps = [math.exp(s - m) for s in scores]
        z = sum(exps)
        return [e / z for e in exps]

    def predict_win_probs(self, features: list[dict]) -> list[dict]:
        scores = []
        for f in features:
            s = sum(self.coef[k] * f[k] for k in self.coef)
            s *= f.get("risk_penalty", 1.0)
            scores.append(s)
        probs = self._softmax(scores)
        result = []
        for f, p in zip(features, probs):
            result.append({**f, "win_prob": p})
        return self._apply_favorite_trust_adjustment(result)

    def _apply_favorite_trust_adjustment(self, rows: list[dict]) -> list[dict]:
        ranked = sorted(rows, key=lambda x: x["win_prob"], reverse=True)
        fav = ranked[0]
        second = ranked[1] if len(ranked) > 1 else fav
        odds_ratio_proxy = fav["win_prob"] / max(second["win_prob"], 1e-6)

        score = 1.0
        reasons = []
        if odds_ratio_proxy < 1.5:
            score -= 0.2
            reasons.append("オッズ集中度が低い")
        if fav.get("risk_penalty", 1.0) < 0.85:
            score -= 0.3
            reasons.append("凡走リスクが高い")
        if abs(fav.get("weight_carried", 55.0) - 55.0) > 2:
            score -= 0.1
            reasons.append("斤量条件が重い")

        multiplier = 1.0
        if score < 0.4:
            multiplier = 1.25
        elif score < 0.6:
            multiplier = 1.15

        if multiplier > 1.0 and len(ranked) >= 3:
            ranked[1]["win_prob"] *= multiplier
            ranked[2]["win_prob"] *= multiplier
            norm = sum(r["win_prob"] for r in ranked)
            for r in ranked:
                r["win_prob"] /= norm

        for r in ranked:
            r["favorite_trust_score"] = max(min(score, 1.0), 0.0)
            r["favorite_trust_reasons"] = reasons
        return ranked
