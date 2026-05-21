"""
SportDevs adapter — Football, Basketball, Tennis, Baseball и др.
Документация: https://sportdevs.com/
"""
import requests
from datetime import datetime, timezone
from models import MatchScore, Sport
from .base import BaseAdapter

_SPORT_MAP = {
    "football":    Sport.FOOTBALL,
    "basketball":  Sport.BASKETBALL,
    "tennis":      Sport.TENNIS,
}

# Продължителност на мач в секунди (за elapsed_pct)
_DURATION = {
    Sport.FOOTBALL:    5400,   # 90 мин
    Sport.BASKETBALL:  2880,   # 48 мин NBA
    Sport.TENNIS:      7200,   # ~2 ч среден тенис
}


class SportDevsAdapter(BaseAdapter):
    BASE = "https://api.sportdevs.com"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": api_key,
            "Accept": "application/json",
        })

    def _get(self, path: str, **params) -> dict | list:
        r = self.session.get(f"{self.BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_score(self, match_id: str) -> MatchScore:
        # SportDevs връща различна структура по спорт — опитваме football първо
        for sport_path, sport_enum in [
            ("/football/matches", Sport.FOOTBALL),
            ("/basketball/matches", Sport.BASKETBALL),
            ("/tennis/matches", Sport.TENNIS),
        ]:
            try:
                data = self._get(f"{sport_path}/{match_id}")
                return self._parse(data, sport_enum)
            except Exception:
                continue
        raise ValueError(f"Не намерих мач {match_id} в SportDevs")

    def _parse(self, data: dict, sport: Sport) -> MatchScore:
        home = data.get("homeTeam", data.get("home_team", {}))
        away = data.get("awayTeam", data.get("away_team", {}))

        score = data.get("score", data.get("result", {}))
        score_a = float(score.get("home", score.get("homeScore", 0)))
        score_b = float(score.get("away", score.get("awayScore", 0)))

        # Период / половина / сет
        period      = data.get("currentPeriod", data.get("period", 1))
        total_periods = 4 if sport == Sport.BASKETBALL else (2 if sport == Sport.FOOTBALL else 3)

        # Elapsed — опитваме от gameTime или startTime
        elapsed_pct = 0.0
        if gt := data.get("gameTime", data.get("elapsed")):
            elapsed_pct = min(float(gt) / _DURATION.get(sport, 5400), 1.0)

        # Tennis специфика — сетове
        extra = {}
        if sport == Sport.TENNIS:
            sets = data.get("sets", [])
            extra["sets"] = sets
            total_periods = data.get("numberOfSets", 3)

        return MatchScore(
            sport=sport,
            match_id=str(data.get("id", "")),
            team_a=home.get("name", "Home"),
            team_b=away.get("name", "Away"),
            score_a=score_a,
            score_b=score_b,
            period=int(period),
            total_periods=total_periods,
            elapsed_pct=elapsed_pct,
            extra=extra,
        )

    def find_match_id(self, team_a: str, team_b: str) -> str | None:
        """Търси в live + upcoming за всички спортове."""
        for path in ["/football/matches/live", "/basketball/matches/live", "/tennis/matches/live"]:
            try:
                matches = self._get(path)
                ta, tb = team_a.lower(), team_b.lower()
                for m in matches:
                    hn = m.get("homeTeam", {}).get("name", "").lower()
                    an = m.get("awayTeam", {}).get("name", "").lower()
                    if (ta in hn and tb in an) or (tb in hn and ta in an):
                        return str(m["id"])
            except Exception:
                continue
        return None
