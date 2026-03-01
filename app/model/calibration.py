import math


class PlattCalibrator:
    def __init__(self, a: float = 1.0, b: float = 0.0):
        self.a = a
        self.b = b

    def transform(self, p: float) -> float:
        p = min(max(p, 1e-6), 1 - 1e-6)
        logit = math.log(p / (1 - p))
        z = self.a * logit + self.b
        return 1.0 / (1.0 + math.exp(-z))

    def transform_many(self, probs: list[float]) -> list[float]:
        vals = [self.transform(p) for p in probs]
        s = sum(vals)
        return [v / s for v in vals] if s > 0 else probs
