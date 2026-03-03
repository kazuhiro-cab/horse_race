from __future__ import annotations

import logging
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
        self._logger = logging.getLogger(__name__)
        self._entries_cache: dict[str, list[dict]] = {}
        self._win_odds_cache: dict[str, dict] = {}

    def _throttle(self):
        time.sleep(REQUEST_INTERVAL_SEC)

    def _norm_race_no(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*R", text, flags=re.IGNORECASE)
        if not m:
            return None
        n = int(m.group(1))
        return n if 1 <= n <= 12 else None

    def _extract_venue(self, text: str) -> str | None:
        return next((v for v in JRA_VENUES if v in text), None)

    def _extract_surface_distance(self, text: str) -> tuple[str | None, int | None]:
        m = re.search(r"(芝|ダート|障害)\s*([0-9]{3,4})\s*(?:メートル|m)", text)
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
        m = re.search(r"発走時刻[:：]\s*(\d{1,2})時(\d{2})分", text)
        if m:
            return f"{int(m.group(1)):02d}:{m.group(2)}"
        m = re.search(r"(\d{1,2}:\d{2})", text)
        return m.group(1) if m else None

    def _extract_field_size(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*頭", text)
        return int(m.group(1)) if m else None

    def _iter_candidate_blocks(self, html_text: str):
        for m in re.finditer(r"<(tr|li|div|p|h1|h2)[^>]*>(.*?)</\1>", html_text, flags=re.DOTALL | re.IGNORECASE):
            text = re.sub(r"<[^>]+>", " ", m.group(2))
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                yield text

    def _build_records_from_html(self, html_pages: list[str], date: str) -> list[dict]:
        records: dict[tuple[str, int], dict] = {}
        ymd = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")

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

        out = []
        for (venue, race_no), rec in sorted(records.items(), key=lambda x: (x[0][0], x[0][1])):
            out.append(
                {
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
                }
            )
        return out

    def _parse_entries_and_odds(self, race_key: str, html_text: str) -> None:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, flags=re.DOTALL | re.IGNORECASE)
        entries: list[dict] = []
        win_odds: dict[str, float] = {}
        for r in rows:
            txt = re.sub(r"<[^>]+>", " ", r)
            txt = re.sub(r"\s+", " ", txt).strip()
            m = re.match(r"^(\d+)\s+(\d+)\s+(.+?)\s+([0-9]+\.?[0-9]*)\s*\(", txt)
            if not m:
                continue
            gate = int(m.group(1))
            num = int(m.group(2))
            name = m.group(3).strip()
            odd = float(m.group(4))
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
            win_odds[str(num)] = odd
        self._entries_cache[race_key] = sorted(entries, key=lambda x: x["number"])
        self._win_odds_cache[race_key] = win_odds

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()
        rows: list[dict] = []
        ymd = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://www.jra.go.jp/keiba/calendar/", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_selector("a[onclick*='accessD.html']", timeout=15000)
                self._logger.info("JRA calendar HTML: %s", page.content())

                # カレンダーから出馬表ページへ遷移
                page.evaluate("doAction('/JRADB/accessD.html','pw01dli00/F3')")
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(1200)
                select_html = page.content()
                self._logger.info("JRA accessD selection HTML: %s", select_html)

                links = []
                for href in re.findall(r'href=["\']([^"\']+)["\']', select_html):
                    u = urljoin("https://www.jra.go.jp", href)
                    if "accessD.html?CNAME=" in u and u not in links:
                        links.append(u)

                # ページネーション相当（リンク網羅）
                for u in links:
                    try:
                        page.goto(u, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_selector("tr", timeout=10000)
                        race_html = page.content()
                        self._logger.info("JRA race HTML (%s): %s", u, race_html)
                        parsed = self._build_records_from_html([race_html], date)
                        if not parsed:
                            continue
                        row = parsed[0]
                        if row["date"] != date:
                            # レースページに別日情報が混在する可能性があるため文字列一致を優先
                            body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", race_html))
                            if ymd not in body and date.replace("-", "年", 1).replace("-", "月", 1)[:7] not in body:
                                continue
                        self._parse_entries_and_odds(row["race_key"], race_html)
                        if not row.get("field_size"):
                            row["field_size"] = len(self._entries_cache.get(row["race_key"], [])) or None
                        rows.append(row)
                    except Exception:
                        self._logger.exception("JRA race page parse failed: %s", u)
                        continue
                browser.close()
        except Exception:
            self._logger.exception("JRA fetch_race_list failed")
            return []

        # venue/race_no missingは警告スキップ
        out = []
        seen = set()
        for r in rows:
            if not r.get("venue") or not r.get("race_no"):
                self._logger.warning("JRA skipped row due to missing venue/race_no: %s", r)
                continue
            key = (r["venue"], r["race_no"])
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        return sorted(out, key=lambda x: (x["venue"], x["race_no"]))

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
