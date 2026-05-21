"""
Конфигурация — попълни преди стартиране.
По-добре зареди от .env:  pip install python-dotenv
"""
import os
from dotenv import load_dotenv
load_dotenv()

# ── API ключове ────────────────────────────────────────────────────────────
PANDASCORE_KEY = os.getenv("PANDASCORE_KEY", "")
RIOT_KEY       = os.getenv("RIOT_KEY", "")
SPORTDEVS_KEY  = os.getenv("SPORTDEVS_KEY", "")

# ── Polymarket wallet ──────────────────────────────────────────────────────
PRIVATE_KEY    = os.getenv("POLYMARKET_PRIVATE_KEY", "")   # Polygon wallet

# ── Стратегия ──────────────────────────────────────────────────────────────
EDGE_THRESHOLD  = float(os.getenv("EDGE_THRESHOLD",  "0.05"))
EXIT_THRESHOLD  = float(os.getenv("EXIT_THRESHOLD",  "0.03"))
BET_SIZE_USDC   = float(os.getenv("BET_SIZE_USDC",   "10"))
POLL_INTERVAL   = int(  os.getenv("POLL_INTERVAL",   "5"))

MIN_ELAPSED_PCT = float(os.getenv("MIN_ELAPSED_PCT", "0.05"))
MAX_ELAPSED_PCT = float(os.getenv("MAX_ELAPSED_PCT", "0.90"))

# ── Мачове за следене ──────────────────────────────────────────────────────
# Всеки запис: (sport, match_id_or_teams, polymarket_token_id_A, polymarket_token_id_B)
WATCH_LIST = [
    # Esports (Pandascore)
    {
        "sport":      "lol",
        "match_id":   "auto",          # "auto" = търси по имена
        "team_a":     "UCAM Esports Club",
        "team_b":     "Movistar KOI Fénix",
        "token_a":    "0xTOKEN_UCAM",
        "token_b":    "0xTOKEN_MOVISTAR",
    },
    # Football (SportDevs)
    {
        "sport":      "football",
        "match_id":   "auto",
        "team_a":     "Real Madrid",
        "team_b":     "Barcelona",
        "token_a":    "0xTOKEN_REAL",
        "token_b":    "0xTOKEN_BARCA",
    },
    # Basketball (SportDevs)
    {
        "sport":      "basketball",
        "match_id":   "12345678",      # директен ID ако е известен
        "team_a":     "Lakers",
        "team_b":     "Celtics",
        "token_a":    "0xTOKEN_LAL",
        "token_b":    "0xTOKEN_BOS",
    },
]

# ── Paper trading ──────────────────────────────────────────────────────────
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"
PAPER_BALANCE = float(os.getenv("PAPER_BALANCE", "1000"))
