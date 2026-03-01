from __future__ import annotations

from datetime import datetime

from app import db
from app.i18n import GOING_EN_TO_JA, SURFACE_EN_TO_JA, market_to_ja, org_to_en, org_to_ja, odds_mode_to_en
from app.sources.jra import JraSource
from app.sources.mock import MockSource
from app.sources.nar import NarSource

MARKETS_EN = ["WIN", "PLACE", "BRACKET", "EXACTA", "QUINELLA", "WIDE", "TRIO", "TRIFECTA", "WIN5"]


def _safe_source(org_en: str, use_mock: bool = False):
    if use_mock:
        return MockSource(), True
    if org_en == "JRA":
        return JraSource(), False
    if org_en == "NAR":
        return NarSource(), False
    raise RuntimeError(f"unknown org: {org_en}")


def _source_for_race_org(org_label: str, use_mock: bool = False):
    if use_mock:
        return MockSource()
    org_en = org_to_en(org_label)
    if org_en == "JRA":
        return JraSource()
    if org_en == "NAR":
        return NarSource()
    raise RuntimeError(f"unknown org label: {org_label}")


def fetch_for_date(date: str, org: str = "all", use_mock: bool = False) -> bool:
    db.init_db()
    mock_mode = False
    org_en = org_to_en(org)
    orgs = ["JRA", "NAR"] if org_en.lower() == "all" else [org_en.upper()]
    races_all = []

    for org_code in orgs:
        src, mocked = _safe_source(org_code, use_mock=use_mock)
        mock_mode = mock_mode or mocked
        races = src.fetch_race_list(date, org_code)

        # 全場・全Rを保存（同日同主催の全開催場を自動検出）
        for r in races:
            r["org"] = org_to_ja(r["org"])
            r["surface"] = SURFACE_EN_TO_JA.get(r.get("surface"), r.get("surface"))
            r["going"] = GOING_EN_TO_JA.get(r.get("going"), r.get("going"))
        races_all.extend(races)

    db.upsert_races(races_all)

    for race in races_all:
        src = _source_for_race_org(race["org"], use_mock=use_mock)
        entries = src.fetch_entries(race["race_key"])
        race["field_size"] = len(entries)
        db.upsert_entries(entries)
        pp_rows = []
        for e in entries:
            pp_rows.extend(src.fetch_past_performances(e["horse_key"]))
        db.insert_past_performances(pp_rows)

    # entries取得後の確定頭数を反映
    db.upsert_races(races_all)
    return mock_mode


def snapshot_odds(date: str, mode: str = "前日最終", org: str = "all", use_mock: bool = False) -> bool:
    db.init_db()
    mode_en = odds_mode_to_en(mode) if mode in ("前日最終", "前日発売開始直後", "当日発売開始直後") else mode
    races = db.fetch_races(date=date, org=org)
    if not races:
        fetch_for_date(date, org, use_mock=use_mock)
        races = db.fetch_races(date=date, org=org)

    captured_at = datetime.now().isoformat(timespec="seconds")
    mock_mode = False
    for race in races:
        src = _source_for_race_org(race["org"], use_mock=use_mock)
        for market_en in MARKETS_EN:
            if market_en == "WIN5" and org_to_en(race["org"]) != "JRA":
                continue
            payload = src.fetch_odds_snapshot(race["race_key"], market_en)
            db.insert_odds_snapshot(race["race_key"], captured_at, mode_en, market_to_ja(market_en), payload)
    return mock_mode
