from __future__ import annotations

from datetime import datetime

from app import db
from app.sources.jra import JraSource
from app.sources.mock import MockSource
from app.sources.nar import NarSource


def _safe_source(org: str):
    if org == "JRA":
        return JraSource(), False
    if org == "NAR":
        try:
            return NarSource(), False
        except Exception:
            return MockSource(), True
    return MockSource(), True


def fetch_for_date(date: str, org: str = "all") -> bool:
    db.init_db()
    mock_mode = False
    orgs = ["JRA", "NAR"] if org.lower() == "all" else [org.upper()]
    races_all = []
    for o in orgs:
        src, mocked = _safe_source(o)
        mock_mode = mock_mode or mocked
        try:
            races = src.fetch_race_list(date, o)
        except Exception:
            src = MockSource()
            races = src.fetch_race_list(date, o)
            mock_mode = True
        races_all.extend(races)
    db.upsert_races(races_all)

    for race in races_all:
        src = MockSource() if (mock_mode or race["org"] == "NAR") else JraSource()
        entries = src.fetch_entries(race["race_key"])
        db.upsert_entries(entries)
        pp_rows = []
        for e in entries:
            pp_rows.extend(src.fetch_past_performances(e["horse_key"]))
        db.insert_past_performances(pp_rows)
    return mock_mode


def snapshot_odds(date: str, mode: str = "prevday_last", org: str = "all") -> bool:
    db.init_db()
    races = db.fetch_races(date=date, org=org)
    if not races:
        fetch_for_date(date, org)
        races = db.fetch_races(date=date, org=org)
    captured_at = datetime.now().isoformat(timespec="seconds")
    mock_mode = False
    for race in races:
        src = MockSource() if race["org"] == "NAR" else JraSource()
        for market in ["PLACE", "TRIO", "TRIFECTA"]:
            try:
                payload = src.fetch_odds_snapshot(race["race_key"], market)
            except Exception:
                payload = MockSource().fetch_odds_snapshot(race["race_key"], market)
                mock_mode = True
            db.insert_odds_snapshot(race["race_key"], captured_at, mode, market, payload)
    return mock_mode
