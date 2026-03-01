from app.sources.base import BaseSource


class NarSource(BaseSource):
    def fetch_race_list(self, date: str, org: str) -> list[dict]:
        raise NotImplementedError("NAR source not implemented yet")

    def fetch_entries(self, race_key: str) -> list[dict]:
        raise NotImplementedError("NAR source not implemented yet")

    def fetch_past_performances(self, horse_key: str) -> list[dict]:
        raise NotImplementedError("NAR source not implemented yet")

    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict:
        raise NotImplementedError("NAR source not implemented yet")

    def fetch_results(self, race_key: str) -> dict:
        raise NotImplementedError("NAR source not implemented yet")
