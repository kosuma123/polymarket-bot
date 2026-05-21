from dataclasses import dataclass, field
from enum import Enum


class Sport(str, Enum):
    LOL        = "lol"
    CS2        = "cs2"
    DOTA2      = "dota2"
    VALORANT   = "valorant"
    FOOTBALL   = "football"
    BASKETBALL = "basketball"
    TENNIS     = "tennis"


class Signal(str, Enum):
    BUY  = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class MatchScore:
    """Единен формат — всеки адаптер връща това."""
    sport:         Sport
    match_id:      str
    team_a:        str
    team_b:        str
    score_a:       float          # точки / голове / рунда / гейма
    score_b:       float
    period:        int   = 1      # текуща карта / сет / половина
    total_periods: int   = 1      # BO3=3, BO5=5, football=2, tennis=3/5
    elapsed_pct:   float = 0.0    # 0..1 — колко от мача е изминал
    extra:         dict  = field(default_factory=dict)   # специфични данни


@dataclass
class Position:
    token_id:    str
    size:        float   # брой shares
    entry_price: float
    side:        str     # "BUY" / "SELL"
