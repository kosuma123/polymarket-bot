"""
Basketball probability model.

Базира се на:
  - Текуща разлика в точките
  - Оставащо игрово време
  - Empirical: ~1 точка = ~3% вероятност при 2 мин
"""
import math
from models import MatchScore
from .base import BaseProbModel


def _normal_cdf(x: float) -> float:
    """Стандартна нормална кумулативна функция."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


class BasketballModel(BaseProbModel):
    """
    Approximation: margin / sqrt(possessions_remaining) → z-score.
    Possessions per 48 мин ~ 100. Всяко possession ~ 1 точка очаквано.
    """
    POSSESSIONS_PER_GAME = 100.0
    POINTS_PER_POSSESSION = 1.05

    def implied_prob(self, score: MatchScore) -> float:
        margin = score.score_a - score.score_b
        remaining = 1.0 - score.elapsed_pct

        possessions_left = self.POSSESSIONS_PER_GAME * remaining
        if possessions_left <= 0:
            return 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0)

        # Standard deviation на финалния margin
        std_dev = math.sqrt(possessions_left) * self.POINTS_PER_POSSESSION

        # z = margin / std_dev
        z = margin / std_dev

        return _normal_cdf(z)
