import time

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource
from app.sources.mock import MockSource


class JraSource(BaseSource):
    """Playwright実装差し替えポイント。"""

    def __init__(self):
        self.mock = MockSource()
        self.live_mode = False  # Playwright実装時にTrueへ切替

    def _throttle(self):
        if self.live_mode:
            time.sleep(REQUEST_INTERVAL_SEC)

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()
        return self.mock.fetch_race_list(date, "JRA")

    def fetch_entries(self, race_key: str) -> list[dict]:
        self._throttle()
        return self.mock.fetch_entries(race_key)

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        self._throttle()
        return self.mock.fetch_past_performances(horse_key)

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        self._throttle()
        return self.mock.fetch_odds_snapshot(race_key, market)

    def fetch_results(self, race_key: str) -> dict:
        self._throttle()
        return self.mock.fetch_results(race_key)
