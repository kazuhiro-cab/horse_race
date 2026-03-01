import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from app.config import DB_PATH as CONFIG_DB_PATH, SCHEMA_PATH

DB_PATH = CONFIG_DB_PATH


def _resolve_db_path(db_path: Path | None = None) -> Path:
    return db_path or DB_PATH


def _ensure_dirs(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect(db_path: Path | None = None):
    resolved = _resolve_db_path(db_path)
    _ensure_dirs(resolved)
    con = sqlite3.connect(str(resolved))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    try:
        yield con
    finally:
        con.commit()
        con.close()


def init_db(db_path: Path | None = None) -> None:
    schema = Path(SCHEMA_PATH).read_text(encoding="utf-8")
    with connect(db_path) as con:
        con.executescript(schema)




def reset_db(db_path: Path | None = None) -> Path:
    resolved = _resolve_db_path(db_path)
    if resolved.exists():
        resolved.unlink()
    init_db(resolved)
    return resolved


def upsert_races(rows: Iterable[dict], db_path: Path | None = None) -> None:
    q = """
    INSERT OR REPLACE INTO races
    (race_key, org, date, venue, race_no, distance_m, surface, going, field_size, start_time, grade, fetched_at)
    VALUES (:race_key, :org, :date, :venue, :race_no, :distance_m, :surface, :going, :field_size, :start_time, :grade, :fetched_at)
    """
    with connect(db_path) as con:
        con.executemany(q, list(rows))


def upsert_entries(rows: Iterable[dict], db_path: Path | None = None) -> None:
    q = """
    INSERT OR REPLACE INTO entries
    (race_key, horse_key, horse_name, gate, number, weight_carried, jockey_name, trainer_name, horse_weight_kg, horse_weight_diff)
    VALUES (:race_key, :horse_key, :horse_name, :gate, :number, :weight_carried, :jockey_name, :trainer_name, :horse_weight_kg, :horse_weight_diff)
    """
    with connect(db_path) as con:
        con.executemany(q, list(rows))


def insert_past_performances(rows: Iterable[dict], db_path: Path | None = None) -> None:
    q = """
    INSERT INTO past_performances
    (horse_key, race_date, org, venue, distance_m, surface, going, finish_pos, field_size, time_sec, passing, last3f_sec, weight_carried, jockey_name, class_label, data_missing_flags)
    VALUES (:horse_key, :race_date, :org, :venue, :distance_m, :surface, :going, :finish_pos, :field_size, :time_sec, :passing, :last3f_sec, :weight_carried, :jockey_name, :class_label, :data_missing_flags)
    """
    with connect(db_path) as con:
        con.executemany(q, list(rows))


def insert_odds_snapshot(race_key: str, captured_at: str, mode: str, market: str, payload: dict, db_path: Path | None = None) -> None:
    q = """
    INSERT OR REPLACE INTO odds_snapshots (race_key, captured_at, mode, market, payload_json)
    VALUES (?, ?, ?, ?, ?)
    """
    with connect(db_path) as con:
        con.execute(q, (race_key, captured_at, mode, market, json.dumps(payload, ensure_ascii=False)))


def insert_prediction(race_key: str, predicted_at: str, odds_snapshot_id: str, market: str, payload: dict, db_path: Path | None = None) -> None:
    q = """
    INSERT OR REPLACE INTO predictions (race_key, predicted_at, odds_snapshot_id, market, payload_json)
    VALUES (?, ?, ?, ?, ?)
    """
    with connect(db_path) as con:
        con.execute(q, (race_key, predicted_at, odds_snapshot_id, market, json.dumps(payload, ensure_ascii=False)))


def insert_bankroll_log(row: dict, db_path: Path | None = None) -> None:
    q = """
    INSERT INTO bankroll_log (logged_at, race_key, market, combination, bet_amount, odds, result, payout, bankroll_after)
    VALUES (:logged_at, :race_key, :market, :combination, :bet_amount, :odds, :result, :payout, :bankroll_after)
    """
    with connect(db_path) as con:
        con.execute(q, row)


def fetch_races(date: str | None = None, org: str = "all", db_path: Path | None = None) -> list[dict]:
    where = []
    params: list = []
    if date:
        where.append("date = ?")
        params.append(date)
    if org not in ("all", "全主催"):
        where.append("org = ?")
        params.append(org)
    sql = "SELECT * FROM races"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date, org, venue, race_no"
    with connect(db_path) as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def fetch_entries(race_key: str, db_path: Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        return [dict(r) for r in con.execute("SELECT * FROM entries WHERE race_key = ? ORDER BY number", (race_key,)).fetchall()]


def fetch_latest_odds(race_key: str, mode: str, market: str, db_path: Path | None = None) -> dict | None:
    q = """
    SELECT captured_at, payload_json FROM odds_snapshots
    WHERE race_key = ? AND mode = ? AND market = ?
    ORDER BY captured_at DESC LIMIT 1
    """
    with connect(db_path) as con:
        row = con.execute(q, (race_key, mode, market)).fetchone()
        if not row:
            return None
        return {"captured_at": row["captured_at"], "payload": json.loads(row["payload_json"])}
