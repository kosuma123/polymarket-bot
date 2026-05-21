from abc import ABC, abstractmethod
from models import MatchScore


class BaseProbModel(ABC):
    @abstractmethod
    def implied_prob(self, score: MatchScore) -> float:
        """Върни implied вероятност за победа на team_a (0..1)."""
        ...
