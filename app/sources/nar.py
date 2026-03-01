import time

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource


class NarSource(BaseSource):
    """NAR公式サイトの実データ取得。"""

    def _throttle(self):
        time.sleep(REQUEST_INTERVAL_SEC)

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()
        raise RuntimeError("NARスクレイピング詳細実装が必要です")

    def fetch_entries(self, race_key: str) -> list[dict]:
        raise RuntimeError("NAR entriesスクレイピング詳細実装が必要です")

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        raise RuntimeError("NAR past performancesスクレイピング詳細実装が必要です")

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        raise RuntimeError("NAR oddsスクレイピング詳細実装が必要です")

    def fetch_results(self, race_key: str) -> dict:
        raise RuntimeError("NAR resultスクレイピング詳細実装が必要です")
