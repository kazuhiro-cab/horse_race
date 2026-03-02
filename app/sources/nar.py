from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any
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

    def _extract_links(self, html: str, base: str) -> list[str]:
        links = []
        for href in re.findall(r'href=["\']([^"\']+)["\']', html):
            url = urljoin(base, href)
            if "keiba.go.jp" not in url:
                continue
            if any(k in url.lower() for k in ["todayrace", "racelist", "raceinfo", "shutuba", "result"]):
                if url not in links:
                    links.append(url)
        return links

    def _extract_json_candidates(self, html: str) -> list[Any]:
        out: list[Any] = []
        for script in re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.DOTALL | re.IGNORECASE):
            text = script.strip()
            if not text:
                continue
            for m in re.finditer(r"\{.*\}|\[.*\]", text, flags=re.DOTALL):
                blob = m.group(0)
                try:
                    out.append(json.loads(blob))
                except Exception:
                    continue
        return out

    def _collect_dicts(self, obj: Any) -> list[dict]:
        rows: list[dict] = []
        if isinstance(obj, dict):
            rows.append(obj)
            for v in obj.values():
                rows.extend(self._collect_dicts(v))
        elif isinstance(obj, list):
            for v in obj:
                rows.extend(self._collect_dicts(v))
        return rows

    def _norm_race_no(self, val: Any) -> int | None:
        s = str(val)
        m = re.search(r"(\d{1,2})", s)
        if not m:
            return None
        n = int(m.group(1))
        return n if 1 <= n <= 12 else None

    def _norm_distance_surface(self, raw: str) -> tuple[str | None, int | None]:
        m = re.search(r"(芝|ダート|障害)\s*([0-9]{3,4})\s*m", raw)
        if not m:
            return None, None
        return m.group(1), int(m.group(2))

    def _norm_going(self, raw: str) -> str | None:
        for g in _GOING_VALUES:
            if g in raw:
                return g
        return None

    def _build_records_from_json(self, payloads: list[Any], date: str) -> list[dict]:
        records: dict[tuple[str, int], dict] = {}
        for payload in payloads:
            for d in self._collect_dicts(payload):
                merged = " ".join(str(v) for v in d.values() if isinstance(v, (str, int, float)))
                venue = next((v for v in NAR_VENUES if v in merged), None)
                race_no = self._norm_race_no(d.get("raceNo") or d.get("race_no") or d.get("race") or merged)
                if not venue or not race_no:
                    continue
                surface, distance = self._norm_distance_surface(merged)
                going = self._norm_going(merged)
                tm = re.search(r"(\d{1,2}:\d{2})", merged)
                fs = re.search(r"(\d{1,2})\s*頭", merged)
                rec = records.setdefault((venue, race_no), {"venue": venue, "race_no": race_no})
                if surface:
                    rec["surface"] = surface
                if distance:
                    rec["distance_m"] = distance
                if going:
                    rec["going"] = going
                if tm:
                    rec["start_time"] = tm.group(1)
                if fs:
                    rec["field_size"] = int(fs.group(1))

        out = []
        ymd = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")
        for (venue, race_no), rec in sorted(records.items(), key=lambda x: (x[0][0], x[0][1])):
            required = ["distance_m", "surface", "going", "start_time", "field_size"]
            missing = [k for k in required if rec.get(k) in (None, "")]
            if missing:
                continue
            out.append(
                {
                    "race_key": f"NAR-{ymd}-{venue}-{race_no:02d}",
                    "date": date,
                    "org": "NAR",
                    "venue": venue,
                    "race_no": race_no,
                    "distance_m": int(rec["distance_m"]),
                    "surface": rec["surface"],
                    "going": rec["going"],
                    "start_time": rec["start_time"],
                    "field_size": int(rec["field_size"]),
                    "grade": "",
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
        return out

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()

        seed_urls = [
            "https://www.keiba.go.jp/",
            "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList",
        ]
        html_map: dict[str, str] = {}
        for url in seed_urls:
            try:
                html_map[url] = self._open(url)
            except Exception:
                continue

        for base, html in list(html_map.items()):
            for link in self._extract_links(html, base)[:120]:
                if link in html_map:
                    continue
                try:
                    html_map[link] = self._open(link)
                except Exception:
                    continue

        if not html_map:
            raise RuntimeError("NAR公式サイト接続失敗")

        payloads: list[Any] = []
        for html in html_map.values():
            payloads.extend(self._extract_json_candidates(html))

        races = self._build_records_from_json(payloads, date)
        if not races:
            raise RuntimeError("NARレース情報（距離/馬場/時刻/頭数）の抽出に失敗しました")
        return races

    def fetch_entries(self, race_key: str) -> list[dict]:
        return []

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        return []

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        return {}

    def fetch_results(self, race_key: str) -> dict:
        return {"status": "未確定", "payouts": {}}
