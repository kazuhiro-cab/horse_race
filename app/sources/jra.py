import re
import time
from datetime import datetime

from app.config import REQUEST_INTERVAL_SEC
from app.sources.base import BaseSource


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

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        self._throttle()
        # 実装はJRAカレンダー/レーシングカードページの構造変更に追随可能な軽量パーサ
        url = f"https://www.jra.go.jp/"
        pw, browser, page = self._open(url)
        rows = []
        try:
            text = page.content()
            if "jra" not in text.lower():
                raise RuntimeError("JRA公式サイト接続失敗")
            # 実運用では開催一覧を詳細パースする。ここでは接続確認と既存DB再利用を前提に空配列を返さない。
            # フォーマット未一致時は明示エラー。
            raise RuntimeError("JRAスクレイピング詳細実装が必要です（ページ構造依存）")
        finally:
            browser.close(); pw.stop()
        return rows

    def fetch_entries(self, race_key: str) -> list[dict]:
        raise RuntimeError("JRA entriesスクレイピング詳細実装が必要です")

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        raise RuntimeError("JRA past performancesスクレイピング詳細実装が必要です")

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        raise RuntimeError("JRA oddsスクレイピング詳細実装が必要です")

    def fetch_results(self, race_key: str) -> dict:
        raise RuntimeError("JRA resultスクレイピング詳細実装が必要です")
