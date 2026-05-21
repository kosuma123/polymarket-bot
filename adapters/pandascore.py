"""
Pandascore adapter — покрива LoL, CS2, Dota2, Valorant, R6, CoD и др.
Документация: https://developers.pandascore.co/
"""
import requests
from models import MatchScore, Sport
from .base import BaseAdapter

# Pandascore sport slug → нашия Sport enum
_SLUG_MAP = {
    "league-of-legends": Sport.LOL,
    "cs-go":             Sport.CS2,
    "dota-2":            Sport.DOTA2,
    "valorant":          Sport.VALORANT,
}

# Брой карти за BO формати
_BO_MAP = {
    "best_of_1": 1,
    "best_of_3": 3,
    "best_of_5": 5,
    "best_of_7": 7,
}


class PandascoreAdapter(BaseAdapter):
    BASE = "https://api.pandascore.co"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })

    def _get(self, path: str, **params) -> dict | list:
        r = self.session.get(f"{self.BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_score(self, match_id: str) -> MatchScore:
        data = self._get(f"/matches/{match_id}")

        sport_slug = data.get("videogame", {}).get("slug", "")
        sport = _SLUG_MAP.get(sport_slug, Sport.LOL)

        opponents = data.get("opponents", [])
        team_a = opponents[0]["opponent"]["name"] if len(opponents) > 0 else "Team A"
        team_b = opponents[1]["opponent"]["name"] if len(opponents) > 1 else "Team B"

        results = data.get("results", [])
        score_a = results[0].get("score", 0) if len(results) > 0 else 0
        score_b = results[1].get("score", 0) if len(results) > 1 else 0

        total_periods = _BO_MAP.get(data.get("number_of_games", "best_of_3"), 3)
        period = score_a + score_b + 1  # текуща карта = изиграни + 1

        # Колко от мача е изминал (0..1)
        games = data.get("games", [])
        finished = sum(1 for g in games if g.get("status") == "finished")
        elapsed_pct = finished / total_periods if total_periods else 0.0

        # Специфични данни по спорт
        extra = {}
        if sport == Sport.LOL and games:
            current_game = next((g for g in games if g.get("status") == "running"), None)
            if current_game:
                extra["game_length_s"] = current_game.get("length", 0)

        return MatchScore(
            sport=sport,
            match_id=str(match_id),
            team_a=team_a,
            team_b=team_b,
            score_a=float(score_a),
            score_b=float(score_b),
            period=period,
            total_periods=total_periods,
            elapsed_pct=elapsed_pct,
            extra=extra,
        )

    def find_match_id(self, team_a: str, team_b: str) -> str | None:
        """Търси текущи/предстоящи мачове по имена на отбори."""
        matches = self._get("/matches/running") + self._get("/matches/upcoming", per_page=50)
        ta, tb = team_a.lower(), team_b.lower()
        for m in matches:
            names = [o["opponent"]["name"].lower() for o in m.get("opponents", [])]
            if len(names) == 2 and ta in names[0] and tb in names[1]:
                return str(m["id"])
            if len(names) == 2 and tb in names[0] and ta in names[1]:
                return str(m["id"])
        return None
