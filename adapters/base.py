from abc import ABC, abstractmethod
from models import MatchScore


class BaseAdapter(ABC):
    """Всеки API адаптер имплементира само това."""

    @abstractmethod
    def get_score(self, match_id: str) -> MatchScore:
        """Вземи текущия резултат и върни MatchScore."""
        ...

    @abstractmethod
    def find_match_id(self, team_a: str, team_b: str) -> str | None:
        """Намери match_id по имена на отбори (за auto-detect)."""
        ...
