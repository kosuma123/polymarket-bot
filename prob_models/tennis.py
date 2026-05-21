"""
Tennis probability model — сетове и гейми.

Марковска верига:
  p_game  → вероятност A да спечели геим при сервис
  p_set   → вероятност A да спечели сет
  p_match → вероятност A да спечели мача
"""
import math
from models import MatchScore
from .base import BaseProbModel


def _p_game(p: float) -> float:
    """Вероятност A да спечели геим при сервис = p."""
    # Изчислено чрез геометричен ред за tennis game (4 точки, deuce...)
    q = 1 - p
    return (p**4 * (15 * q**3 - 40 * p * q**2 + 45 * p**2 * q - 24 * p**3 + 10)) / \
           (p**4 + q**4 + 4 * p * q * (p**2 + q**2) + 6 * p**2 * q**2)


def _p_set(p_game_a: float, p_game_b: float, games_a: int = 0, games_b: int = 0) -> float:
    """Probability A wins set от текущ game score (games_a:games_b)."""
    # Опростен: binomial по игри до 6 (или 7 при tiebreak)
    remaining_a = max(6 - games_a, 0)
    remaining_b = max(6 - games_b, 0)
    if remaining_a == 0 and games_a > games_b:
        return 1.0
    if remaining_b == 0 and games_b > games_a:
        return 0.0
    if remaining_a == 0 and remaining_b == 0:
        # Tiebreak
        return p_game_a
    p = p_game_a
    prob = 0.0
    for k in range(remaining_a, remaining_a + remaining_b):
        n = k - 1
        r = remaining_a - 1
        if n < 0 or r < 0 or r > n:
            continue
        binom = math.comb(n, r)
        prob += binom * (p ** remaining_a) * ((1 - p) ** (k - remaining_a))
    return min(max(prob, 0.0), 1.0)


def _p_match(p_set: float, sets_a: int, sets_b: int, best_of: int = 3) -> float:
    """Probability A wins match от текущ set score."""
    sets_needed = math.ceil(best_of / 2)
    remaining_a = sets_needed - sets_a
    remaining_b = sets_needed - sets_b
    if remaining_a <= 0:
        return 1.0
    if remaining_b <= 0:
        return 0.0
    max_sets = remaining_a + remaining_b - 1
    prob = 0.0
    for k in range(remaining_a, max_sets + 1):
        n = k - 1
        r = remaining_a - 1
        if n < 0 or r < 0 or r > n:
            continue
        binom = math.comb(n, r)
        prob += binom * (p_set ** remaining_a) * ((1 - p_set) ** (k - remaining_a))
    return min(max(prob, 0.0), 1.0)


class TennisModel(BaseProbModel):
    """
    Ползва score (сетове) и extra["games_a"], extra["games_b"] ако са налични.
    p_serve = 0.62 (типично за ATP), 0.58 за WTA.
    """
    P_SERVE_ATP = 0.62
    P_SERVE_WTA = 0.58

    def implied_prob(self, score: MatchScore) -> float:
        p_serve = self.P_SERVE_ATP   # може да се конфигурира
        p_game_a = _p_game(p_serve)
        p_game_b = _p_game(p_serve)

        games_a = score.extra.get("games_a", 0)
        games_b = score.extra.get("games_b", 0)

        ps = _p_set(p_game_a, p_game_b, int(games_a), int(games_b))
        pm = _p_match(ps, int(score.score_a), int(score.score_b), score.total_periods)

        return max(0.01, min(0.99, pm))
