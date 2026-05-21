"""
Strategy — сравнява implied_prob (от score) с market_odds (от Polymarket).
Логика:
  • implied > market + edge_threshold  → BUY (пазарът подценява)
  • market  > implied + exit_threshold → SELL / EXIT (пазарът е надминал)
  • иначе                              → HOLD
"""
import logging
from dataclasses import dataclass
from models import Signal, Position

log = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    signal:       Signal
    implied_prob: float
    market_odds:  float
    edge:         float
    note:         str = ""


class Strategy:
    def __init__(
        self,
        edge_threshold:  float = 0.05,   # минимален edge за влизане
        exit_threshold:  float = 0.03,   # edge в обратна посока за изход
        min_elapsed_pct: float = 0.05,   # не залагай в първите 5% от мача
        max_elapsed_pct: float = 0.90,   # не залагай в последните 10%
        min_liquidity:   float = 500.0,  # минимален volume в ордер бука (USDC)
    ):
        self.edge_threshold  = edge_threshold
        self.exit_threshold  = exit_threshold
        self.min_elapsed_pct = min_elapsed_pct
        self.max_elapsed_pct = max_elapsed_pct
        self.min_liquidity   = min_liquidity
        self.position: Position | None = None

    def evaluate(self, implied_prob: float, market_odds: float, elapsed_pct: float) -> StrategyResult:
        edge = implied_prob - market_odds

        # --- Guard: твърде рано / твърде късно ---
        if elapsed_pct < self.min_elapsed_pct:
            return StrategyResult(Signal.HOLD, implied_prob, market_odds, edge, "Твърде рано")
        if elapsed_pct > self.max_elapsed_pct:
            return StrategyResult(Signal.HOLD, implied_prob, market_odds, edge, "Твърде късно")

        # --- Изход (приоритет над влизане) ---
        if self.position and (market_odds - implied_prob) > self.exit_threshold:
            return StrategyResult(Signal.SELL, implied_prob, market_odds, edge, "Reverse edge — EXIT")

        # --- Влизане ---
        if self.position is None and edge > self.edge_threshold:
            return StrategyResult(Signal.BUY, implied_prob, market_odds, edge, "Edge detected — ENTER")

        return StrategyResult(Signal.HOLD, implied_prob, market_odds, edge, "No edge")
