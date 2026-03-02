from __future__ import annotations

import re
import time
from datetime import datetime
from urllib.parse import urljoin

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource

JRA_VENUES = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]
_GOING_VALUES = ("良", "稍重", "重", "不良")


class JraSource(BaseSource):
    def __init__(self):
        self._entries_cache: dict[str, list[dict]] = {}
        self._win_odds_cache: dict[str, dict] = {}

    def _throttle(self):
        time.sleep(REQUEST_INTERVAL_SEC)

    def _open(self, url: str) -> str:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(800)
            return page.content()
        finally:
            browser.close()
            pw.stop()

    def _extract_cname_links(self, html_text: str, base: str) -> list[str]:
        links = []
        for href in re.findall(r'href=["\']([^"\']+)["\']', html_text):
            url = urljoin(base, href)
            if "accessD.html?CNAME=" in url and url not in links:
                links.append(url)
        return links

    def _norm_race_no(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*R", text, flags=re.IGNORECASE)
        if not m:
            return None
        n = int(m.group(1))
        return n if 1 <= n <= 12 else None

    def _extract_venue(self, text: str) -> str | None:
        return next((v for v in JRA_VENUES if v in text), None)

    def _extract_surface_distance(self, text: str) -> tuple[str | None, int | None]:
        m = re.search(r"(芝|ダート|障害)\s*([0-9]{3,4})\s*メートル", text)
        if not m:
            m = re.search(r"(芝|ダート|障害)\s*([0-9]{3,4})\s*m", text)
        if not m:
            return None, None
        return m.group(1), int(m.group(2))

    def _extract_going(self, text: str) -> str | None:
        for g in _GOING_VALUES:
            if g in text:
                return g
        return None

    def _extract_grade(self, text: str) -> str | None:
        m = re.search(r"(G1|G2|G3|J\.G1|J\.G2|J\.G3|L|OP|オープン)", text, flags=re.IGNORECASE)
        return m.group(1).upper() if m else None

    def _extract_start_time(self, text: str) -> str | None:
        m = re.search(r"発走時刻[:：]\s*(\d{1,2}時\d{2}分)", text)
        if m:
            hhmm = m.group(1).replace("時", ":").replace("分", "")
            h, mi = hhmm.split(":")
            return f"{int(h):02d}:{int(mi):02d}"
        m = re.search(r"(\d{1,2}:\d{2})", text)
        return m.group(1) if m else None

    def _extract_field_size(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*頭", text)
        return int(m.group(1)) if m else None

    def _parse_entry_rows(self, race_key: str, html_text: str) -> tuple[list[dict], dict]:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, flags=re.DOTALL | re.IGNORECASE)
        entries = []
        win_odds = {}
        for r in rows:
            txt = re.sub(r"<[^>]+>", " ", r)
            txt = re.sub(r"\s+", " ", txt).strip()
            mnum = re.match(r"^(\d+)\s+(\d+)\s+(.+?)\s+([0-9]+\.?[0-9]*)\s*\(", txt)
            if not mnum:
                continue
            gate = int(mnum.group(1))
            num = int(mnum.group(2))
            name = mnum.group(3).strip()
            odds = float(mnum.group(4))
            entries.append(
                {
                    "race_key": race_key,
                    "horse_key": f"{race_key}-H{num:02d}",
                    "horse_name": name,
                    "gate": gate,
                    "number": num,
                    "weight_carried": 55.0,
                    "jockey_name": None,
                    "trainer_name": None,
                    "horse_weight_kg": None,
                    "horse_weight_diff": None,
                }
            )
            win_odds[str(num)] = odds
        entries.sort(key=lambda x: x["number"])
        return entries, win_odds


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
                grade = self._extract_grade(text)
                if grade:
                    rec["grade"] = grade

        ymd = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")
        out = []
        for (venue, race_no), rec in sorted(records.items(), key=lambda x: (x[0][0], x[0][1])):
            out.append({
                "race_key": f"JRA-{ymd}-{venue}-{race_no:02d}",
                "date": date,
                "org": "JRA",
                "venue": venue,
                "race_no": race_no,
                "distance_m": rec.get("distance_m"),
                "surface": rec.get("surface"),
                "going": rec.get("going"),
                "start_time": rec.get("start_time"),
                "field_size": rec.get("field_size"),
                "grade": rec.get("grade"),
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
            })
        return out

    def _parse_race_page(self, url: str, date: str) -> dict | None:
        html_text = self._open(url)
        body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_text))
        venue = self._extract_venue(body)
        race_no = self._norm_race_no(body)
        if not venue or not race_no:
            return None
        surface, distance = self._extract_surface_distance(body)
        going = self._extract_going(body)
        start_time = self._extract_start_time(body)
        grade = self._extract_grade(body)
        race_key = f"JRA-{datetime.strptime(date, '%Y-%m-%d').strftime('%Y%m%d')}-{venue}-{race_no:02d}"
        entries, win_odds = self._parse_entry_rows(race_key, html_text)
        field_size = len(entries) if entries else None
        self._entries_cache[race_key] = entries
        self._win_odds_cache[race_key] = win_odds
        return {
            "race_key": race_key,
            "date": date,
            "org": "JRA",
            "venue": venue,
            "race_no": race_no,
            "distance_m": distance,
            "surface": surface,
            "going": going,
            "start_time": start_time,
            "field_size": field_size,
            "grade": grade,
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        }

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()
        cal_html = self._open("https://www.jra.go.jp/keiba/calendar/")
        if "doAction('/JRADB/accessD.html'" not in cal_html:
            raise RuntimeError("JRAカレンダーページ構造取得失敗")

        select_html = self._open("https://www.jra.go.jp/JRADB/accessD.html")
        links = self._extract_cname_links(select_html, "https://www.jra.go.jp")
        if not links:
            raise RuntimeError("JRA出馬表リンク取得失敗")

        rows = []
        seen = set()
        for u in links:
            row = self._parse_race_page(u, date)
            if not row:
                continue
            key = row["race_key"]
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return sorted(rows, key=lambda x: (x["venue"], x["race_no"]))

    def fetch_entries(self, race_key: str) -> list[dict]:
        return self._entries_cache.get(race_key, [])

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        return []

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        if market.upper() == "WIN":
            return self._win_odds_cache.get(race_key, {})
        return {}

    def fetch_results(self, race_key: str) -> dict:
        return {"status": "未確定", "payouts": {}}
