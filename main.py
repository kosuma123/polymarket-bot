"""
Polymarket Multi-Sport Bot
─────────────────────────
PAPER_TRADING=true  →  симулация с реални пазарни данни
PAPER_TRADING=false →  ⚠️  РЕАЛНИ ПАРИ
"""
import logging
import threading
import time
import sys
from models import Sport, Signal, Position
from registry import SportRegistry
from strategy import Strategy
from startup import run_checks
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def build_client():
    """Избери paper или live client."""
    if config.PAPER_TRADING:
        from paper_client import PaperClient
        return PaperClient(starting_usdc=config.PAPER_BALANCE)
    else:
        # Финална защита — изисква ръчно потвърждение в терминала
        log.warning("══════════════════════════════════════════════")
        log.warning("  ⚠️   LIVE РЕЖИМ — ще се изпращат РЕАЛНИ ОРДЕРИ")
        log.warning("══════════════════════════════════════════════")
        confirm = input("Напиши 'LIVE' за потвърждение: ").strip()
        if confirm != "LIVE":
            log.info("Отказано — стартирам в PAPER режим.")
            config.PAPER_TRADING = True
            from paper_client import PaperClient
            return PaperClient(starting_usdc=config.PAPER_BALANCE)
        from polymarket_client import PolymarketClient
        return PolymarketClient(private_key=config.PRIVATE_KEY)


class MatchWorker(threading.Thread):
    def __init__(self, watch: dict, registry: SportRegistry, poly):
        super().__init__(
            name=f"{watch['team_a'][:10]}v{watch['team_b'][:10]}",
            daemon=True,
        )
        self.watch    = watch
        self.registry = registry
        self.poly     = poly
        self.strategy = Strategy(
            edge_threshold  = config.EDGE_THRESHOLD,
            exit_threshold  = config.EXIT_THRESHOLD,
            min_elapsed_pct = config.MIN_ELAPSED_PCT,
            max_elapsed_pct = config.MAX_ELAPSED_PCT,
        )
        self.sport    = Sport(watch["sport"])
        self.match_id = watch.get("match_id", "auto")
        self._running = True

    def _resolve_match_id(self) -> bool:
        if self.match_id != "auto":
            return True
        found = self.registry.find_match(
            self.sport, self.watch["team_a"], self.watch["team_b"]
        )
        if found:
            self.match_id = found
            log.info(f"Auto-resolved match_id: {self.match_id}")
            return True
        log.warning(f"Не намерих мач: {self.watch['team_a']} vs {self.watch['team_b']}")
        return False

    def run(self):
        mode = "[PAPER]" if config.PAPER_TRADING else "[LIVE]"
        log.info(f"{mode} Старт: {self.watch['team_a']} vs {self.watch['team_b']}")

        while self._running and not self._resolve_match_id():
            time.sleep(30)

        adapter = self.registry.get_adapter(self.sport)
        model   = self.registry.get_model(self.sport)

        while self._running:
            try:
                score        = adapter.get_score(self.match_id)
                implied_prob = model.implied_prob(score)
                market_odds  = self.poly.get_midpoint(self.watch["token_a"])
                spread       = self.poly.get_spread(self.watch["token_a"])
                result       = self.strategy.evaluate(
                    implied_prob, market_odds, score.elapsed_pct
                )

                mode = "[PAPER]" if config.PAPER_TRADING else "[LIVE]"
                log.info(
                    f"{mode} {score.team_a} {score.score_a:.0f}:{score.score_b:.0f} {score.team_b} │ "
                    f"Implied={implied_prob:.2%} Market={market_odds:.2%} "
                    f"Spread={spread:.4f} Edge={result.edge:+.2%} → "
                    f"{result.signal.value} ({result.note})"
                )

                if result.signal == Signal.BUY:
                    resp = self.poly.buy(self.watch["token_a"], config.BET_SIZE_USDC)
                    if resp.get("status") == "filled":
                        price = market_odds
                        self.strategy.position = Position(
                            token_id    = self.watch["token_a"],
                            size        = config.BET_SIZE_USDC / price,
                            entry_price = price,
                            side        = "BUY",
                        )

                elif result.signal == Signal.SELL and self.strategy.position:
                    resp = self.poly.sell(
                        self.strategy.position.token_id,
                        self.strategy.position.size,
                    )
                    if resp.get("status") == "filled":
                        self.strategy.position = None

                if score.elapsed_pct >= 1.0:
                    log.info(f"Мачът приключи: {self.watch['team_a']} vs {self.watch['team_b']}")
                    break

            except Exception as e:
                log.error(f"Грешка: {e}", exc_info=True)

            time.sleep(config.POLL_INTERVAL)

    def stop(self):
        self._running = False


def main():
    # Startup проверки — спира ако има критични грешки в live режим
    if not run_checks() and not config.PAPER_TRADING:
        log.error("Startup failed — спирам. Поправи конфигурацията.")
        sys.exit(1)

    poly = build_client()

    registry = SportRegistry({
        "pandascore_key": config.PANDASCORE_KEY,
        "riot_key":       config.RIOT_KEY,
        "sportdevs_key":  config.SPORTDEVS_KEY,
    })

    workers = [MatchWorker(w, registry, poly) for w in config.WATCH_LIST]
    for w in workers:
        w.start()

    mode = "PAPER 🧪" if config.PAPER_TRADING else "LIVE ⚠️"
    log.info(f"Следя {len(workers)} мача │ Режим: {mode} │ Ctrl+C за спиране.")

    try:
        while any(w.is_alive() for w in workers):
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Прекъсване — спирам нишките...")
        for w in workers:
            w.stop()
        poly.cancel_all()
        if config.PAPER_TRADING:
            poly.summary()
        log.info("Край.")


if __name__ == "__main__":
    main()
