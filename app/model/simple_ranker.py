from __future__ import annotations

import math

from app.model.base import BaseModel


class SimpleRanker(BaseModel):
    def __init__(self):
        self.feature_names = ["finish_proxy", "distance_fit", "weight_carried", "rest_weeks"]
        self.default_coef = {"finish_proxy": -0.7, "distance_fit": 1.3, "weight_carried": -0.05, "rest_weeks": -0.03}
        self._sk_model = None
        try:
            from sklearn.linear_model import LogisticRegression

            self._sk_model = LogisticRegression()
            import numpy as np

            self._sk_model.classes_ = np.array([0, 1])
            self._sk_model.coef_ = np.array([[self.default_coef[k] for k in self.feature_names]], dtype=float)
            self._sk_model.intercept_ = np.array([0.0], dtype=float)
            self._sk_model.n_features_in_ = len(self.feature_names)
        except Exception:
            self._sk_model = None

    def _softmax(self, scores: list[float]) -> list[float]:
        m = max(scores)
        exps = [math.exp(s - m) for s in scores]
        z = sum(exps)
        return [e / z for e in exps]

    def predict_win_probs(self, features: list[dict]) -> list[dict]:
        if self._sk_model is not None:
            X = [[f[k] for k in self.feature_names] for f in features]
            scores = [float(x) for x in self._sk_model.decision_function(X)]
        else:
            scores = [sum(self.default_coef[k] * f[k] for k in self.feature_names) for f in features]

        scores = [s * f.get("risk_penalty", 1.0) for s, f in zip(scores, features)]
        probs = self._softmax(scores)
        result = [{**f, "win_prob": p} for f, p in zip(features, probs)]
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

        multiplier = 1.25 if score < 0.4 else 1.15 if score < 0.6 else 1.0
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
