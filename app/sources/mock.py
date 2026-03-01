import json
import re
from datetime import datetime, timedelta
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
        self._normalize_race_cards()

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

    def _normalize_race_cards(self) -> None:
        """モックの見た目を実運用に近づける（頭数/発走時刻/馬場種別）。"""
        grouped: dict[tuple[str, str, str], list[dict]] = {}
        for race in self._races:
            grouped.setdefault((race["date"], race["org"], race["venue"]), []).append(race)

        for (_, org, _), races in grouped.items():
            races.sort(key=lambda x: x["race_no"])
            base_time = datetime(2000, 1, 1, 9, 50)
            for race in races:
                no = int(race["race_no"])
                # 頭数: 10〜18を循環（すべて3頭になる問題を回避）
                race["field_size"] = 10 + ((no - 1) % 9)
                race["start_time"] = (base_time + timedelta(minutes=(no - 1) * 30)).strftime("%H:%M")

                if org == "JRA":
                    if no % 6 == 0:
                        race["surface"] = "JUMP"
                        race["going"] = "GOOD"
                    else:
                        race["surface"] = "TURF" if no % 3 != 0 else "DIRT"
                        race["going"] = "FIRM" if race["surface"] == "TURF" else "GOOD"
                else:
                    race["surface"] = "DIRT"
                    race["going"] = "GOOD"

                self._ensure_entries_match_field_size(race)
                self._ensure_odds_for_race(race)

    def _ensure_entries_match_field_size(self, race: dict) -> None:
        race_key = race["race_key"]
        need = int(race["field_size"])
        current = self._entries.get(race_key, [])
        if len(current) == need:
            return

        seed = current[0] if current else {
            "horse_name": "モックホース",
            "weight_carried": 55.0,
            "jockey_name": "モック騎手",
            "trainer_name": "モック調教師",
            "horse_weight_kg": 470,
            "horse_weight_diff": 0,
        }

        rebuilt = []
        for n in range(1, need + 1):
            gate = ((n - 1) // 2) + 1
            rebuilt.append(
                {
                    "race_key": race_key,
                    "horse_key": f"{race_key}-H{n:02d}",
                    "horse_name": f"{seed.get('horse_name', 'モックホース')}{n}",
                    "gate": gate,
                    "number": n,
                    "weight_carried": float((seed.get("weight_carried") if seed.get("weight_carried") is not None else 55.0)) + ((n % 3) - 1) * 0.5,
                    "jockey_name": seed.get("jockey_name", "モック騎手"),
                    "trainer_name": seed.get("trainer_name", "モック調教師"),
                    "horse_weight_kg": float((seed.get("horse_weight_kg") if seed.get("horse_weight_kg") is not None else 470)) + (n % 5),
                    "horse_weight_diff": float((seed.get("horse_weight_diff") if seed.get("horse_weight_diff") is not None else 0)),
                }
            )
        self._entries[race_key] = rebuilt

    def _ensure_odds_for_race(self, race: dict) -> None:
        race_key = race["race_key"]
        size = int(race["field_size"])
        odds = self._odds.setdefault(race_key, {})

        odds["WIN"] = {str(i): round(max(2.0, 30.0 - i * 1.1), 1) for i in range(1, size + 1)}
        odds["PLACE"] = {str(i): round(max(2.0, 18.0 - i * 0.5), 1) for i in range(1, size + 1)}

        trio_key = "-".join(map(str, [1, 2, 3]))
        odds.setdefault("TRIO", {})
        odds["TRIO"][trio_key] = float(850)

        odds.setdefault("TRIFECTA", {})
        odds["TRIFECTA"]["1-2-3"] = float(3200)
        odds["TRIFECTA"]["1-3-2"] = float(2800)
        odds["TRIFECTA"]["2-1-3"] = float(2600)

        # ペア系
        pair_payload = {"1-2": 120.0, "1-3": 150.0, "2-3": 180.0}
        for k in ["BRACKET", "EXACTA", "QUINELLA", "WIDE"]:
            odds[k] = dict(pair_payload)

        # WIN5 は限定的に保持
        odds.setdefault("WIN5", {"1-1-1-1-1": 5000.0})

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
