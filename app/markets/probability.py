from __future__ import annotations

import itertools


def place_probabilities(win_probs: dict[int, float]) -> dict[int, float]:
    n = len(win_probs)
    result = {k: 0.0 for k in win_probs}
    for horse in win_probs:
        others = [h for h in win_probs if h != horse]
        p1 = win_probs[horse]
        p2 = sum(win_probs[o] * (win_probs[horse] / max(1 - win_probs[o], 1e-9)) for o in others)
        p3 = 0.0
        for a, b in itertools.permutations(others, 2):
            p3 += win_probs[a] * (win_probs[b] / max(1 - win_probs[a], 1e-9)) * (win_probs[horse] / max(1 - win_probs[a] - win_probs[b], 1e-9))
        result[horse] = min(p1 + p2 + p3, 1.0) if n >= 3 else min(p1 + p2, 1.0)
    return result


def trio_probabilities(win_probs: dict[int, float]) -> dict[str, float]:
    # Harville (1973) 近似。馬間相互作用を無視した独立仮定に基づく。
    combos = {}
    horses = list(win_probs)
    for trio in itertools.combinations(horses, 3):
        p = 0.0
        for order in itertools.permutations(trio):
            p += trifecta_order_prob(win_probs, order)
        combos["-".join(map(str, sorted(trio)))] = p
    return combos


def trifecta_probabilities(win_probs: dict[int, float]) -> dict[str, float]:
    # Harville (1973) 近似。馬間相互作用を無視した独立仮定に基づく。
    probs = {}
    for order in itertools.permutations(win_probs.keys(), 3):
        probs["-".join(map(str, order))] = trifecta_order_prob(win_probs, order)
    return probs


def trifecta_order_prob(win_probs: dict[int, float], order: tuple[int, int, int]) -> float:
    a, b, c = order
    pa = win_probs[a]
    pb = win_probs[b] / max(1 - pa, 1e-9)
    pc = win_probs[c] / max(1 - pa - win_probs[b], 1e-9)
    return max(pa * pb * pc, 0.0)
