"""
Football (soccer) probability model.

Използва Dixon-Coles inspired подход:
  - Базирано на текущ score + оставащо време
  - Поасонов модел за очакваните голове
"""
import math
from models import MatchScore
from .base import BaseProbModel


def _poisson_prob(lam: float, k: int) -> float:
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _score_prob_matrix(lam_a: float, lam_b: float, max_goals: int = 8):
    """Матрица на вероятностите за всеки краен резултат."""
    matrix = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            matrix[(i, j)] = _poisson_prob(lam_a, i) * _poisson_prob(lam_b, j)
    return matrix


def _win_draw_loss(lam_a: float, lam_b: float):
    matrix = _score_prob_matrix(lam_a, lam_b)
    win_a = sum(v for (i, j), v in matrix.items() if i > j)
    draw  = sum(v for (i, j), v in matrix.items() if i == j)
    win_b = sum(v for (i, j), v in matrix.items() if i < j)
    return win_a, draw, win_b


class FootballModel(BaseProbModel):
    """
    Базова λ = 1.35 гола на отбор за 90 мин (среден Premier League).
    Коригира се спрямо текущ score и оставащо време.
    """
    BASE_LAMBDA = 1.35

    def implied_prob(self, score: MatchScore) -> float:
        goals_a = score.score_a
        goals_b = score.score_b
        remaining = 1.0 - score.elapsed_pct   # fraction от мача останало

        # Очаквани голове в оставащото време
        lam_a = self.BASE_LAMBDA * remaining
        lam_b = self.BASE_LAMBDA * remaining

        # Симулираме от текущия score нататък
        win_a, draw, win_b = _win_draw_loss(lam_a, lam_b)

        # Текущ score е база — ако A води 2:0 при 80', вероятността е висока
        if goals_a > goals_b:
            # A трябва да задържи
            prob_a = win_a + draw * 0.3
        elif goals_b > goals_a:
            # B трябва да задържи
            prob_a = win_a
        else:
            # Равен — нормален разпад
            prob_a = win_a + draw * 0.5

        # Нормализирай
        total = win_a + draw + win_b
        if total == 0:
            return 0.5

        # Претегли с "предимство от score"
        score_edge = (goals_a - goals_b) * 0.12 * score.elapsed_pct
        result = prob_a / total + score_edge

        return max(0.01, min(0.99, result))
