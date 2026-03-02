from __future__ import annotations

import html
import re
import time
from datetime import datetime
from urllib.parse import urljoin

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource

NAR_VENUES = ["門別", "盛岡", "水沢", "浦和", "船橋", "大井", "川崎", "金沢", "笠松", "名古屋", "園田", "姫路", "高知", "佐賀", "帯広"]
_GOING_VALUES = ("良", "稍重", "重", "不良")


class NarSource(BaseSource):
    """NAR公式サイトの実データ取得。"""

    def _throttle(self):
        time.sleep(REQUEST_INTERVAL_SEC)

    def _open(self, url: str) -> str:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return page.content()
        finally:
            browser.close()
            pw.stop()

    def _extract_links(self, html_text: str, base: str) -> list[str]:
        links = []
        for href in re.findall(r'href=["\']([^"\']+)["\']', html_text):
            url = urljoin(base, html.unescape(href))
            if "keiba.go.jp" not in url:
                continue
            if "/KeibaWeb/TodayRaceInfo/RaceList" in url and url not in links:
                links.append(url)
        return links

    def _norm_race_no(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*R", text, flags=re.IGNORECASE)
        if not m:
            m = re.search(r"\b(\d{1,2})\b", text)
        if not m:
            return None
        n = int(m.group(1))
        return n if 1 <= n <= 12 else None

    def _extract_venue(self, text: str) -> str | None:
        return next((v for v in NAR_VENUES if v in text), None)

    def _extract_surface_distance(self, text: str) -> tuple[str | None, int | None]:
        m = re.search(r"(芝|ダート|障害)\s*([0-9]{3,4})\s*m", text)
        if not m:
            m = re.search(r"([0-9]{3,4})\s*m\s*(芝|ダート|障害)", text)
            if not m:
                return None, None
            return m.group(2), int(m.group(1))
        return m.group(1), int(m.group(2))

    def _extract_going(self, text: str) -> str | None:
        for g in _GOING_VALUES:
            if f"馬場:{g}" in text or f"馬場状態:{g}" in text or f"/{g}" in text:
                return g
        for g in _GOING_VALUES:
            if g in text:
                return g
        return None

    def _extract_start_time(self, text: str) -> str | None:
        m = re.search(r"(\d{1,2}:\d{2})", text)
        return m.group(1) if m else None

    def _extract_field_size(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*頭", text)
        return int(m.group(1)) if m else None

    def _iter_candidate_blocks(self, html_text: str):
        for m in re.finditer(r"<(tr|li|div)[^>]*>(.*?)</\1>", html_text, flags=re.DOTALL | re.IGNORECASE):
            block = m.group(2)
            text = re.sub(r"<[^>]+>", " ", block)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                yield text

    def _build_records_from_html(self, html_pages: list[str], date: str) -> list[dict]:
        records: dict[tuple[str, int], dict] = {}

        for html_text in html_pages:
            for text in self._iter_candidate_blocks(html_text):
                venue = self._extract_venue(text)
                race_no = self._norm_race_no(text)
                if not venue or not race_no:
                    continue

                rec = records.setdefault((venue, race_no), {"venue": venue, "race_no": race_no})
                surface, distance = self._extract_surface_distance(text)
                if surface:
                    rec["surface"] = surface
                if distance:
                    rec["distance_m"] = distance
                going = self._extract_going(text)
                if going:
                    rec["going"] = going
                start = self._extract_start_time(text)
                if start:
                    rec["start_time"] = start
                field_size = self._extract_field_size(text)
                if field_size:
                    rec["field_size"] = field_size

        ymd = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")
        out = []
        for (venue, race_no), rec in sorted(records.items(), key=lambda x: (x[0][0], x[0][1])):
            if not rec.get("venue") or not rec.get("race_no"):
                continue
            out.append(
                {
                    "race_key": f"NAR-{ymd}-{venue}-{race_no:02d}",
                    "date": date,
                    "org": "NAR",
                    "venue": venue,
                    "race_no": race_no,
                    "distance_m": rec.get("distance_m"),
                    "surface": rec.get("surface"),
                    "going": rec.get("going"),
                    "start_time": rec.get("start_time"),
                    "field_size": rec.get("field_size"),
                    "grade": None,
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
        return out

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()

        seed_urls = [
            "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop",
            "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList",
        ]
        html_map: dict[str, str] = {}
        for url in seed_urls:
            try:
                html_map[url] = self._open(url)
            except Exception:
                continue

        for base, html_text in list(html_map.items()):
            for link in self._extract_links(html_text, base)[:200]:
                if link in html_map:
                    continue
                if f"k_raceDate={date.replace('-', '%2f')}" not in link.replace('%2F', '%2f') and f"k_raceDate={date.replace('-', '/')}" not in link:
                    continue
                try:
                    html_map[link] = self._open(link)
                except Exception:
                    continue

        if not html_map:
            raise RuntimeError("NAR公式サイト接続失敗")

        races = self._build_records_from_html(list(html_map.values()), date)
        if not races:
            raise RuntimeError("NAR開催場名またはレース番号を抽出できませんでした")
        return races

    def fetch_entries(self, race_key: str) -> list[dict]:
        return []

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        return []

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        return {}

    def fetch_results(self, race_key: str) -> dict:
        return {"status": "未確定", "payouts": {}}
