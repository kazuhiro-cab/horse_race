import json
from pathlib import Path

from app.config import SAMPLES_DIR
from app.sources.base import BaseSource


class MockSource(BaseSource):
    def __init__(self, sample_dir: Path = SAMPLES_DIR):
        self.sample_dir = sample_dir
        self._races = self._load_json("races.json")
        self._entries = self._load_json("entries.json")
        self._pp = self._load_json("past_performances.json")
        self._odds = self._load_json("odds.json")

    def _load_json(self, name: str):
        return json.loads((self.sample_dir / name).read_text(encoding="utf-8"))

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        rows = [r for r in self._races if r["date"] == date]
        if org.lower() != "all":
            rows = [r for r in rows if r["org"] == org.upper()]
        return rows

    def fetch_entries(self, race_key: str) -> list[dict]:
        return self._entries.get(race_key, [])

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        return self._pp.get(horse_key, [])

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        race_odds = self._odds.get(race_key, {})
        return race_odds.get(market.upper(), {})
