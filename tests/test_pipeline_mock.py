from datetime import date

from app import db
from app.pipeline.fetch import fetch_for_date, snapshot_odds
from app.pipeline.predict import predict_race


def test_fetch_predict_pipeline_mock(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.sqlite3")
    d = "2026-03-01"
    db.init_db(db.DB_PATH)
    fetch_for_date(d, "all")
    snapshot_odds(d, mode="prevday_last", org="all")

    races = db.fetch_races(date=d)
    assert races
    assert len(races) >= 36
    out = predict_race(races[0]["race_key"], odds_mode="prevday_last", bankroll=10000)
    assert "bets" in out

    with db.connect() as con:
        pred_n = con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        log_n = con.execute("SELECT COUNT(*) FROM bankroll_log").fetchone()[0]
    assert pred_n >= 1
    assert log_n >= 1


def test_backtest_date_only_not_zero_when_logs_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t2.sqlite3")
    d = "2026-03-01"
    db.init_db(db.DB_PATH)
    fetch_for_date(d, "all")
    snapshot_odds(d, mode="prevday_last", org="all")
    races = db.fetch_races(date=d)
    predict_race(races[0]["race_key"], odds_mode="prevday_last", bankroll=10000)

    from app.pipeline.backtest import run_backtest

    stats = run_backtest(d, d)
    assert stats["回収率"] >= 0.0
    with db.connect() as con:
        n = con.execute("SELECT COUNT(*) FROM bankroll_log WHERE result IN ('的中','ハズレ')").fetchone()[0]
    assert n >= 1
