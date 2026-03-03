from __future__ import annotations

import html
import logging
import re
import time
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource

NAR_VENUES = ["門別", "盛岡", "水沢", "浦和", "船橋", "大井", "川崎", "金沢", "笠松", "名古屋", "園田", "姫路", "高知", "佐賀", "帯広"]
_GOING_VALUES = ("良", "稍重", "重", "不良")


class NarSource(BaseSource):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._result_url_cache: dict[str, str] = {}

    def _throttle(self):
        time.sleep(REQUEST_INTERVAL_SEC)

    def _norm_race_no(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*R", text, flags=re.IGNORECASE)
        if not m:
            return None
        n = int(m.group(1))
        return n if 1 <= n <= 12 else None

    def _extract_venue(self, text: str) -> str | None:
        return next((v for v in NAR_VENUES if v in text), None)

    def _extract_surface_distance(self, text: str) -> tuple[str | None, int | None]:
        m = re.search(r"(芝|ダート|障害|直)\s*([0-9]{3,4})\s*m", text)
        if not m:
            return None, None
        surf = m.group(1)
        if surf == "直":
            surf = None
        return surf, int(m.group(2))

    def _extract_going(self, text: str) -> str | None:
        for g in _GOING_VALUES:
            if g in text:
                return g
        return None

    def _extract_start_time(self, text: str) -> str | None:
        m = re.search(r"(\d{1,2}:\d{2})", text)
        return m.group(1) if m else None

    def _extract_field_size(self, text: str) -> int | None:
        m = re.search(r"(\d{1,2})\s*頭", text)
        if m:
            return int(m.group(1))
        # NAR当日メニューは最後の列が頭数のことがある
        m = re.search(r"\s(\d{1,2})\s*(?:オッズ|映像|成績|$)", text)
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

        out = []
        for (venue, race_no), rec in sorted(records.items(), key=lambda x: (x[0][0], x[0][1])):
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

    def _race_list_links(self, top_html: str, date: str) -> list[str]:
        target_slash = date.replace("-", "/")
        links: list[str] = []
        for href in re.findall(r'href=["\']([^"\']+)["\']', top_html):
            u = urljoin("https://www.keiba.go.jp", html.unescape(href))
            if "/KeibaWeb/TodayRaceInfo/RaceList" not in u:
                continue
            q = parse_qs(urlparse(u).query)
            d = q.get("k_raceDate", [""])[0].replace("%2f", "/").replace("%2F", "/")
            if d and d != target_slash:
                continue
            if u not in links:
                links.append(u)

        baba_codes = set(re.findall(r'k_babaCode=([0-9]{2})', top_html))
        if not baba_codes:
            baba_codes.update(re.findall(r'value=["\']([0-9]{2})["\']', top_html))
        for code in sorted(baba_codes):
            u = (
                "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList"
                f"?k_raceDate={target_slash}&k_babaCode={code}"
            )
            if u not in links:
                links.append(u)
        return links

    def fetch_race_list(self, date: str, org: str, progress_callback=None) -> list[dict]:
        self._throttle()
        rows: list[dict] = []
        visited_urls: list[str] = []
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()

                # 指定URLそのものにもアクセスしてHTML全文を取得
                if progress_callback:
                    progress_callback("レース情報取得中...（NAR RaceList 入口）")
                    progress_callback("アクセス中: https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList")
                page.goto("https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList", wait_until="domcontentloaded", timeout=30000)
                self._logger.info("NAR RaceList HTML (direct): %s", page.content())

                if progress_callback:
                    progress_callback("アクセス中: https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop")
                page.goto("https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_selector("a[href*='/KeibaWeb/TodayRaceInfo/RaceList']", timeout=15000)
                top_html = page.content()
                self._logger.info("NAR TodayRaceInfoTop HTML: %s", top_html)

                links = self._race_list_links(top_html, date)
                if not links:
                    raise RuntimeError("NAR開催ページリンクを取得できませんでした（RaceList導線が見つかりません）。")

                for u in links:
                    visited_urls.append(u)
                    if progress_callback:
                        parsed = urlparse(u)
                        q = parse_qs(parsed.query)
                        baba = q.get("k_babaCode", ["?"])[0]
                        progress_callback(f"レース情報取得中...（NAR RaceList baba={baba}）")
                        progress_callback(f"アクセス中: {u}")
                    try:
                        page.goto(u, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(600)
                        race_html = page.content()
                        self._logger.info("NAR RaceList HTML (%s): %s", u, race_html)
                        parsed_rows = self._build_records_from_html([race_html], date)
                        if not parsed_rows:
                            raise RuntimeError(f"NARレース情報の解析結果が空です: {u}")
                        rows.extend(parsed_rows)
                        if progress_callback:
                            for rr in parsed_rows:
                                progress_callback(f"レース情報取得中...（NAR {rr['venue']} {rr['race_no']}R）")
                        # 成績リンクをキャッシュ
                        for href in re.findall(r'href=["\']([^"\']+)["\']', race_html):
                            ru = urljoin("https://www.keiba.go.jp", html.unescape(href))
                            if "RaceMarkTable" not in ru and "RaceResult" not in ru:
                                continue
                            q2 = parse_qs(urlparse(ru).query)
                            rno = q2.get("k_raceNo", [""])[0]
                            if not rno:
                                continue
                            for rr in self._build_records_from_html([race_html], date):
                                if int(rno) == int(rr["race_no"]):
                                    self._result_url_cache[rr["race_key"]] = ru

                    except Exception as exc:
                        self._logger.exception("NAR RaceList parse failed: %s", u)
                        raise RuntimeError(f"NARレースページ解析に失敗しました: {u} ({exc})") from exc
                browser.close()
        except Exception as e:
            self._logger.exception("NAR fetch_race_list failed")
            raise RuntimeError(f"NARデータの取得に失敗しました: {e}") from e

        out = []
        seen = set()
        for r in rows:
            if not r.get("venue") or not r.get("race_no"):
                self._logger.warning("NAR skipped row due to missing venue/race_no: %s", r)
                continue
            key = (r["venue"], r["race_no"])
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        if not out:
            last_url = visited_urls[-1] if visited_urls else "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList"
            raise RuntimeError(f"NAR実データ取得結果が空です。最終アクセス先: {last_url}")
        return sorted(out, key=lambda x: (x["venue"], x["race_no"]))

    def fetch_entries(self, race_key: str) -> list[dict]:
        return []

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        return []

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        return {}

    def fetch_results(self, race_key: str) -> dict:
        url = self._result_url_cache.get(race_key)
        if not url:
            return {"status": "未確定", "payouts": {}}
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(800)
                html_text = page.content()
                browser.close()
        except Exception:
            self._logger.exception("NAR result fetch failed: %s", race_key)
            return {"status": "未確定", "payouts": {}}

        body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_text))
        payouts: dict[str, dict] = {
            "単勝": {}, "複勝": {}, "枠連": {}, "馬連": {}, "馬単": {}, "ワイド": {}, "三連複": {}, "三連単": {}
        }
        market_map = {"単勝":"単勝","複勝":"複勝","枠複":"枠連","馬複":"馬連","馬単":"馬単","ワイド":"ワイド","3連複":"三連複","3連単":"三連単"}
        for mk, out in market_map.items():
            for m in re.finditer(rf"{re.escape(mk)}\s+([0-9\-]+)\s+([0-9,]+)円", body):
                payouts[out][m.group(1)] = float(m.group(2).replace(",", ""))

        status = "確定" if any(payouts[k] for k in payouts) else "未確定"
        return {"status": status, "payouts": payouts}
