from app.markets.bets import build_ev_bets, kelly_half_fraction


def test_kelly_fraction_and_caps():
    assert kelly_half_fraction(1.5, 5.0) > 0
    assert kelly_half_fraction(0.9, 5.0) == 0

    bets = build_ev_bets({"A": 0.2, "B": 0.1}, {"A": 10.0, "B": 20.0}, bankroll=10000)
    assert bets
    assert all(b["bet_amount"] >= 100 for b in bets)
    assert sum(b["bet_amount"] for b in bets) <= 3000
