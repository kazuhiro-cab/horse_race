from __future__ import annotations

from datetime import datetime

from app import db
from app.i18n import GOING_EN_TO_JA, SURFACE_EN_TO_JA, market_to_ja, odds_mode_to_en, org_to_en, org_to_ja
from app.sources.jra import JraSource
from app.sources.nar import NarSource

MARKETS_EN = ["WIN", "PLACE", "BRACKET", "EXACTA", "QUINELLA", "WIDE", "TRIO", "TRIFECTA", "WIN5"]


def _safe_source(org_en: str):
    if org_en == "JRA":
        return JraSource()
    if org_en == "NAR":
        return NarSource()
    raise RuntimeError(f"unknown org: {org_en}")


def fetch_for_date(date: str, org: str = "all", progress_callback=None) -> None:
    db.init_db()
    org_en = org_to_en(org)
    orgs = ["JRA", "NAR"] if org_en.lower() == "all" else [org_en.upper()]
    src_map = {code: _safe_source(code) for code in orgs}
    races_all = []

    for org_code in orgs:
        src = src_map[org_code]
        if progress_callback:
            progress_callback(f"レース情報取得中...（{org_code}）")
        races = src.fetch_race_list(date, org_code, progress_callback=progress_callback)
        for r in races:
            r["org"] = org_to_ja(r["org"])
            r["surface"] = SURFACE_EN_TO_JA.get(r.get("surface"), r.get("surface"))
            r["going"] = GOING_EN_TO_JA.get(r.get("going"), r.get("going"))
        races_all.extend(races)
        if progress_callback:
            for rr in races:
                progress_callback(f"レース情報取得中...（{rr.get('venue', '?')}）")

    db.upsert_races(races_all)

    for race in races_all:
        src = src_map[org_to_en(race["org"])]
        entries = src.fetch_entries(race["race_key"])
        race["field_size"] = len(entries) if entries else race.get("field_size")
        if entries:
            db.upsert_entries(entries)
            pp_rows = []
            for e in entries:
                pp_rows.extend(src.fetch_past_performances(e["horse_key"]))
            if pp_rows:
                db.insert_past_performances(pp_rows)

    db.upsert_races(races_all)


def snapshot_odds(date: str, mode: str = "前日最終", org: str = "all") -> None:
    db.init_db()
    mode_en = odds_mode_to_en(mode) if mode in ("前日最終", "前日発売開始直後", "当日発売開始直後") else mode
    races = db.fetch_races(date=date, org=org)
    if not races:
        fetch_for_date(date, org)
        races = db.fetch_races(date=date, org=org)

    captured_at = datetime.now().isoformat(timespec="seconds")
    src_map = {"JRA": JraSource(), "NAR": NarSource()}
    # ensure caches are populated for odds by fetching race list once per org
    orgs = sorted(set(org_to_en(r["org"]) for r in races))
    for o in orgs:
        try:
            src_map[o].fetch_race_list(date, o)
        except Exception:
            pass

    for race in races:
        src = src_map[org_to_en(race["org"])]
        for market_en in MARKETS_EN:
            if market_en == "WIN5" and org_to_en(race["org"]) != "JRA":
                continue
            payload = src.fetch_odds_snapshot(race["race_key"], market_en)
            if payload:
                db.insert_odds_snapshot(race["race_key"], captured_at, mode_en, market_to_ja(market_en), payload)
