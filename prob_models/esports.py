"""
Esports probability model — BO1 / BO3 / BO5.

Логика:
  1. Базова вероятност от текущия score (карти спечелени).
  2. Корекция за in-game напредък ако има допълнителни данни (gold, kills).
  3. Регресия към 0.5 в началото на мача (малко информация).
"""
import math
from models import MatchScore
from .base import BaseProbModel


def _win_prob_from_series(wins_a: int, wins_b: int, best_of: int) -> float:
    """
    Binomial probability — колко вероятно е A да спечели серията
    при текущ score wins_a:wins_b в BO(best_of).

    Приема p=0.5 за single game (neutral prior).
    """
    wins_needed = math.ceil(best_of / 2)
    remaining_a = wins_needed - wins_a
    remaining_b = wins_needed - wins_b
    if remaining_a <= 0:
        return 1.0
    if remaining_b <= 0:
        return 0.0

    max_games = remaining_a + remaining_b - 1
    p = 0.5
    prob_a = 0.0
    for k in range(remaining_a, max_games + 1):
        # A печели точно remaining_a от k игри (последната е win за A)
        n = k - 1
        r = remaining_a - 1
        binom = math.comb(n, r)
        prob_a += binom * (p ** k) * ((1 - p) ** (k - remaining_a))
    return prob_a


def _gold_lead_adjustment(extra: dict, elapsed_pct: float) -> float:
    """
    Ако имаме gold lead данни от Riot, добавяме корекция.
    Типично gold advantage от 5000+ при 30+ мин е силен сигнал.
    """
    gold_a = extra.get("gold_a", 0)
    gold_b = extra.get("gold_b", 0)
    if gold_a == 0 and gold_b == 0:
        return 0.0
    total = gold_a + gold_b
    if total == 0:
        return 0.0
    raw = (gold_a / total) - 0.5   # -0.5 .. +0.5
    # По-силен сигнал в края на мача
    weight = elapsed_pct * 0.3
    return raw * weight


class EsportsModel(BaseProbModel):
    def implied_prob(self, score: MatchScore) -> float:
        wins_a = int(score.score_a)
        wins_b = int(score.score_b)
        best_of = score.total_periods

        series_prob = _win_prob_from_series(wins_a, wins_b, best_of)

        # Gold/kill корекция (само ако Riot данни са налични)
        adj = _gold_lead_adjustment(score.extra, score.elapsed_pct)

        # Регресия към 0.5 в самото начало (ниска информация)
        info_weight = min(score.elapsed_pct * 3, 1.0)
        blended = 0.5 + (series_prob - 0.5) * info_weight

        result = blended + adj
        return max(0.01, min(0.99, result))
