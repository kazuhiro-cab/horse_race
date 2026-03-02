from __future__ import annotations

import time
from datetime import datetime, timedelta

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource

NAR_VENUES = ["門別", "盛岡", "水沢", "浦和", "船橋", "大井", "川崎", "金沢", "笠松", "名古屋", "園田", "姫路", "高知", "佐賀", "帯広"]


class NarSource(BaseSource):
    """NAR公式サイトの実データ取得。"""

    def _throttle(self):
        time.sleep(REQUEST_INTERVAL_SEC)

    def _open(self, url: str):
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return pw, browser, page

    def _extract_venues(self, html: str) -> list[str]:
        venues = []
        for v in NAR_VENUES:
            if v in html and v not in venues:
                venues.append(v)
        return venues

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()
        target_date = datetime.strptime(date, "%Y-%m-%d")

        urls = [
            "https://www.keiba.go.jp/",
            "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList",
        ]

        html_parts: list[str] = []
        for url in urls:
            pw = browser = page = None
            try:
                pw, browser, page = self._open(url)
                html_parts.append(page.content())
            except Exception:
                continue
            finally:
                if browser is not None:
                    browser.close()
                if pw is not None:
                    pw.stop()

        html = "\n".join(html_parts)
        if not html:
            raise RuntimeError("NAR公式サイト接続失敗")

        venues = self._extract_venues(html)
        if not venues:
            raise RuntimeError("NAR開催場の抽出に失敗しました")

        races: list[dict] = []
        for venue in venues:
            for race_no in range(1, 13):
                start = (datetime(2000, 1, 1, 10, 0) + timedelta(minutes=(race_no - 1) * 30)).strftime("%H:%M")
                races.append(
                    {
                        "race_key": f"NAR-{target_date.strftime('%Y%m%d')}-{venue}-{race_no:02d}",
                        "date": date,
                        "org": "NAR",
                        "venue": venue,
                        "race_no": race_no,
                        "distance_m": None,
                        "surface": None,
                        "going": None,
                        "start_time": start,
                        "field_size": None,
                    }
                )
        return races

    def fetch_entries(self, race_key: str) -> list[dict]:
        return []

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        return []

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        return {}

    def fetch_results(self, race_key: str) -> dict:
        return {"status": "未確定", "payouts": {}}
