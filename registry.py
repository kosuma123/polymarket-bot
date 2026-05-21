"""
SportRegistry — map от Sport към правилния адаптер и probability модел.
Автоматично избира адаптера по спорт.
"""
from models import Sport
from adapters import PandascoreAdapter, RiotAdapter, SportDevsAdapter
from prob_models import EsportsModel, FootballModel, BasketballModel, TennisModel


class SportRegistry:
    def __init__(self, config: dict):
        """
        config = {
            "pandascore_key": "...",
            "riot_key":       "...",
            "sportdevs_key":  "...",
        }
        """
        self._adapters = {}
        self._models   = {}

        # Инициализирай адаптерите само ако са конфигурирани
        if config.get("pandascore_key"):
            ps = PandascoreAdapter(config["pandascore_key"])
            for sport in [Sport.LOL, Sport.CS2, Sport.DOTA2, Sport.VALORANT]:
                self._adapters[sport] = ps
                self._models[sport]   = EsportsModel()

        if config.get("riot_key"):
            riot = RiotAdapter(config["riot_key"])
            # Riot само за LOL live данни (като допълнение към Pandascore)
            self._adapters["riot_live"] = riot

        if config.get("sportdevs_key"):
            sd = SportDevsAdapter(config["sportdevs_key"])
            self._adapters[Sport.FOOTBALL]   = sd
            self._adapters[Sport.BASKETBALL] = sd
            self._adapters[Sport.TENNIS]     = sd
            self._models[Sport.FOOTBALL]     = FootballModel()
            self._models[Sport.BASKETBALL]   = BasketballModel()
            self._models[Sport.TENNIS]       = TennisModel()

    def get_adapter(self, sport: Sport):
        if sport not in self._adapters:
            raise ValueError(f"Няма конфигуриран адаптер за {sport}")
        return self._adapters[sport]

    def get_model(self, sport: Sport):
        if sport not in self._models:
            raise ValueError(f"Няма probability модел за {sport}")
        return self._models[sport]

    def find_match(self, sport: Sport, team_a: str, team_b: str) -> str | None:
        """Автоматично намери match_id по отбори."""
        adapter = self.get_adapter(sport)
        return adapter.find_match_id(team_a, team_b)
