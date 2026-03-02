from abc import ABC, abstractmethod


class BaseModel(ABC):
    @abstractmethod
    def predict_win_probs(self, features: list[dict]) -> list[dict]: ...
