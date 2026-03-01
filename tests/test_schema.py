from app import db


def test_schema_created(tmp_path):
    db_path = tmp_path / "t.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as con:
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for t in {"races", "entries", "past_performances", "odds_snapshots", "predictions", "bankroll_log"}:
        assert t in names
