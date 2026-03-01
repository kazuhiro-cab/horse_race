import json
import re
from pathlib import Path

from app.config import SAMPLES_DIR
from app.sources.base import BaseSource


class MockSource(BaseSource):
    def __init__(self, sample_dir: Path = SAMPLES_DIR):
        self.sample_dir = sample_dir
        self._races = self._load_json("races.json")
        self._entries = self._load_json("entries.json")
        self._pp = self._load_json("past_performances.json")
        self._odds = self._load_json("odds.json")
        self._results = self._load_json("results.json")
        self._expand_full_race_card(final_race_no=12)

    def _load_json(self, name: str):
        return json.loads((self.sample_dir / name).read_text(encoding="utf-8"))

    def _expand_full_race_card(self, final_race_no: int = 12) -> None:
        """モックでも全場・全R取得動作を確認できるように不足Rを補完する。"""
        grouped: dict[tuple[str, str, str], list[dict]] = {}
        for race in self._races:
            key = (race["date"], race["org"], race["venue"])
            grouped.setdefault(key, []).append(race)

        new_races: list[dict] = []
        for (_, _, _), races in grouped.items():
            by_no = {r["race_no"]: r for r in races}
            template = sorted(races, key=lambda x: x["race_no"])[0]

            for no in range(1, final_race_no + 1):
                if no in by_no:
                    continue

                generated = dict(template)
                generated["race_no"] = no
                generated["race_key"] = re.sub(r"-\d{2}$", f"-{no:02d}", template["race_key"])
                generated["start_time"] = None
                new_races.append(generated)

                # entries をテンプレートから複製
                template_entries = self._entries.get(template["race_key"], [])
                cloned_entries = []
                for idx, entry in enumerate(template_entries, start=1):
                    copied = dict(entry)
                    copied["race_key"] = generated["race_key"]
                    copied["horse_key"] = f"{entry['horse_key']}_R{no:02d}_{idx}"
                    cloned_entries.append(copied)
                self._entries[generated["race_key"]] = cloned_entries

                # odds/results をテンプレートから複製
                self._odds[generated["race_key"]] = dict(self._odds.get(template["race_key"], {}))
                self._results[generated["race_key"]] = dict(self._results.get(template["race_key"], {"status": "未確定", "payouts": {}}))

        self._races.extend(new_races)

    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        rows = [r for r in self._races if r["date"] == date]
        if org.lower() != "all":
            rows = [r for r in rows if r["org"] == org.upper()]
        return sorted(rows, key=lambda x: (x["venue"], x["race_no"]))

    def fetch_entries(self, race_key: str) -> list[dict]:
        return self._entries.get(race_key, [])

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        return self._pp.get(horse_key, [])

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        return self._odds.get(race_key, {}).get(market.upper(), {})

    def fetch_results(self, race_key: str) -> dict:
        return self._results.get(race_key, {})
