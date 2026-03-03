from abc import ABC, abstractmethod


class BaseSource(ABC):
    @abstractmethod
    def fetch_race_list(self, date: str, org: str, progress_callback=None) -> list[dict]: ...

    @abstractmethod
    def fetch_entries(self, race_key: str) -> list[dict]: ...

    @abstractmethod
    def fetch_past_performances(self, horse_key: str) -> list[dict]: ...

    @abstractmethod
    def fetch_odds_snapshot(self, race_key: str, market: str) -> dict: ...

    @abstractmethod
    def fetch_results(self, race_key: str) -> dict: ...
