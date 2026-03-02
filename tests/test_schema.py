from app import db


def test_schema_created(tmp_path):
    db_path = tmp_path / "t.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as con:
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for t in {"races", "entries", "past_performances", "odds_snapshots", "predictions", "bankroll_log"}:
        assert t in names


def test_reset_db_recreates_schema(tmp_path):
    db_path = tmp_path / "r.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as con:
        con.execute("INSERT INTO races (race_key, org, date, venue, race_no) VALUES ('X','JRA','2026-03-01','中山',1)")
    db.reset_db(db_path)
    with db.connect(db_path) as con:
        cnt = con.execute("SELECT COUNT(*) FROM races").fetchone()[0]
    assert cnt == 0
