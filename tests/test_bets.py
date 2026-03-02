from app.markets.probability import place_probabilities, trifecta_probabilities, trio_probabilities


def test_probabilities_range_and_sum():
    win = {1: 0.5, 2: 0.3, 3: 0.2}
    place = place_probabilities(win)
    trio = trio_probabilities(win)
    trifecta = trifecta_probabilities(win)

    assert abs(sum(win.values()) - 1.0) < 1e-9
    for d in [place, trio, trifecta]:
        for v in d.values():
            assert 0.0 <= v <= 1.0
