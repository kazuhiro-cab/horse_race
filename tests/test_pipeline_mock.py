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
    out = predict_race(races[0]["race_key"], odds_mode="prevday_last", bankroll=10000)
    assert "bets" in out

    with db.connect() as con:
        pred_n = con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        log_n = con.execute("SELECT COUNT(*) FROM bankroll_log").fetchone()[0]
    assert pred_n >= 1
    assert log_n >= 1
