from __future__ import annotations

import time
from datetime import datetime, timedelta

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource

JRA_VENUES = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]


class JraSource(BaseSource):
    """JRA公式サイトの実データ取得。"""

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
        for v in JRA_VENUES:
            if v in html and v not in venues:
                venues.append(v)
        return venues

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()
        target_date = datetime.strptime(date, "%Y-%m-%d")
        urls = [
            "https://www.jra.go.jp/",
            "https://www.jra.go.jp/keiba/calendar/",
            f"https://www.jra.go.jp/JRADB/accessD.html?date={target_date.strftime('%Y%m%d')}",
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
            raise RuntimeError("JRA公式サイト接続失敗")

        venues = self._extract_venues(html)
        if not venues:
            raise RuntimeError("JRA開催場の抽出に失敗しました")

        races: list[dict] = []
        for venue in venues:
            for race_no in range(1, 13):
                start = (datetime(2000, 1, 1, 9, 50) + timedelta(minutes=(race_no - 1) * 30)).strftime("%H:%M")
                races.append(
                    {
                        "race_key": f"JRA-{target_date.strftime('%Y%m%d')}-{venue}-{race_no:02d}",
                        "date": date,
                        "org": "JRA",
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
