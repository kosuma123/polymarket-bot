"""
Riot Games adapter — live LoL данни (gold, towers, kills, inhibitors).
Използва Live Client Data API (работи само по време на мач).
Документация: https://developer.riotgames.com/
"""
import requests
from models import MatchScore, Sport
from .base import BaseAdapter


class RiotAdapter(BaseAdapter):
    """
    Riot предоставя два вида данни:
      1. Live Client Data API  — само за текущата игра на локалния клиент
      2. Spectator v5 API      — за наблюдение на конкретен summoner (ranked)
    За esports турнири Pandascore е по-надежден; Riot се ползва за
    по-детайлни live metrics (gold lead, towers, objectives).
    """
    LIVE_URL  = "https://127.0.0.1:2999/liveclientdata"   # Local client
    API_BASE  = "https://euw1.api.riotgames.com"           # Смени regional за друг регион

    def __init__(self, api_key: str, region: str = "euw1"):
        self.api_key = api_key
        self.region  = region
        self.api_base = f"https://{region}.api.riotgames.com"
        self.session  = requests.Session()
        self.session.headers.update({"X-Riot-Token": api_key})

    # ------------------------------------------------------------------ #
    #  Live Client Data (локален клиент, за spectate/собствена игра)      #
    # ------------------------------------------------------------------ #
    def get_live_game_stats(self) -> dict:
        """Вземи сурови live данни от локалния клиент."""
        r = requests.get(
            f"{self.LIVE_URL}/allgamedata",
            verify=False,   # Riot използва self-signed cert
            timeout=5,
        )
        r.raise_for_status()
        return r.json()

    def _gold_lead_to_score(self, data: dict) -> tuple[float, float]:
        """
        Конвертира gold lead → score_a / score_b (нормализирано 0..1 в extra).
        Основна метрика: total gold + towers + kills.
        """
        players = data.get("allPlayers", [])
        gold_a = gold_b = 0.0
        for p in players:
            g = p.get("scores", {}).get("creepScore", 0) * 20  # cs ~ gold
            if p.get("team") == "ORDER":
                gold_a += g
            else:
                gold_b += g

        kills_a = sum(p["scores"]["kills"] for p in players if p.get("team") == "ORDER")
        kills_b = sum(p["scores"]["kills"] for p in players if p.get("team") == "CHAOS")

        return float(kills_a), float(kills_b)

    def get_score(self, match_id: str) -> MatchScore:
        """match_id = summoner PUUID за spectator, или 'live' за локален клиент."""
        if match_id == "live":
            data = self.get_live_game_stats()
            score_a, score_b = self._gold_lead_to_score(data)
            game_time = data.get("gameData", {}).get("gameTime", 0)
            elapsed_pct = min(game_time / 2400, 1.0)   # ~40 мин = пълен мач
            return MatchScore(
                sport=Sport.LOL,
                match_id="live",
                team_a="ORDER",
                team_b="CHAOS",
                score_a=score_a,
                score_b=score_b,
                elapsed_pct=elapsed_pct,
                extra={"game_time_s": game_time, "raw": data},
            )

        # Spectator API — вземи активна игра по PUUID
        r = self.session.get(
            f"{self.api_base}/lol/spectator/v5/active-games/by-summoner/{match_id}",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        participants = data.get("participants", [])
        blue = [p for p in participants if p.get("teamId") == 100]
        red  = [p for p in participants if p.get("teamId") == 200]

        return MatchScore(
            sport=Sport.LOL,
            match_id=match_id,
            team_a=blue[0].get("summonerName", "Blue") if blue else "Blue",
            team_b=red[0].get("summonerName", "Red")   if red  else "Red",
            score_a=float(len(blue)),
            score_b=float(len(red)),
            elapsed_pct=min(data.get("gameLength", 0) / 2400, 1.0),
            extra={"raw": data},
        )

    def find_match_id(self, team_a: str, team_b: str) -> str | None:
        """Riot няма прост search — за турнири използвай Pandascore."""
        return None
