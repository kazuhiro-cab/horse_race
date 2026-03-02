from __future__ import annotations

import time
from datetime import date, timedelta

import schedule

from app.pipeline.fetch import fetch_for_date, snapshot_odds
from app.pipeline.predict import predict_race
from app import db


def _today() -> str:
    return date.today().isoformat()


def job_fetch_dates():
    fetch_for_date(_today(), "all")
    fetch_for_date((date.today() + timedelta(days=1)).isoformat(), "all")


def job_entries():
    fetch_for_date(_today(), "all")


def job_prevday_snapshots():
    snapshot_odds((date.today() + timedelta(days=1)).isoformat(), mode="prevday_last", org="all")


def job_dayof_open():
    snapshot_odds(_today(), mode="dayof_open", org="all")


def job_batch_predict():
    races = db.fetch_races(date=_today(), org="all")
    for r in races:
        predict_race(r["race_key"])


def run_scheduler():
    schedule.every().day.at("06:00").do(job_fetch_dates)
    schedule.every().day.at("08:00").do(job_entries)
    for t in ["17:00", "20:00", "22:00"]:
        schedule.every().day.at(t).do(job_prevday_snapshots)
    schedule.every().day.at("09:00").do(job_batch_predict)
    schedule.every(30).minutes.do(job_dayof_open)

    while True:
        schedule.run_pending()
        time.sleep(1)
