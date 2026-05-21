"""
PaperClient — идентичен интерфейс с PolymarketClient.
Всички ордери са симулирани. Пазарните данни са РЕАЛНИ (от Polymarket CLOB).
"""
import logging
import requests
from datetime import datetime

log = logging.getLogger(__name__)

CLOB = "https://clob.polymarket.com"


class PaperClient:
    def __init__(self, starting_usdc: float = 1000.0):
        self.balance   = starting_usdc
        self._start    = starting_usdc
        self.positions: dict[str, dict] = {}
        self.trades:    list[dict]       = []
        self._price_cache: dict[str, float] = {}
        self._session  = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ── Реални пазарни данни ────────────────────────────────────────────
    def get_midpoint(self, token_id: str) -> float:
        """Взима реалната midpoint цена от Polymarket CLOB."""
        try:
            r = self._session.get(
                f"{CLOB}/book",
                params={"token_id": token_id},
                timeout=5,
            )
            r.raise_for_status()
            book = r.json()
            bids = book.get("bids", [])
            asks = book.get("asks", [])
            bid  = float(bids[0]["price"]) if bids else 0.0
            ask  = float(asks[0]["price"]) if asks else 1.0
            mid  = round((bid + ask) / 2, 4)
            self._price_cache[token_id] = mid
            return mid
        except Exception as e:
            log.warning(f"Грешка при get_midpoint ({token_id[:12]}…): {e}")
            return self._price_cache.get(token_id, 0.5)

    def get_spread(self, token_id: str) -> float:
        try:
            r = self._session.get(f"{CLOB}/book", params={"token_id": token_id}, timeout=5)
            book = r.json()
            bids = book.get("bids", [])
            asks = book.get("asks", [])
            if not bids or not asks:
                return 1.0
            return round(float(asks[0]["price"]) - float(bids[0]["price"]), 4)
        except Exception:
            return 0.02

    def get_market(self, condition_id: str) -> dict:
        r = self._session.get(f"{CLOB}/markets/{condition_id}", timeout=5)
        r.raise_for_status()
        return r.json()

    # ── Симулирани ордери ───────────────────────────────────────────────
    def buy(self, token_id: str, usdc_amount: float) -> dict:
        price = self.get_midpoint(token_id)

        if usdc_amount > self.balance:
            log.warning(f"[PAPER] ❌ BUY отхвърлен — баланс ${self.balance:.2f} < ${usdc_amount:.2f}")
            return {"status": "rejected", "reason": "insufficient_balance"}

        size          = round(usdc_amount / price, 4)
        self.balance -= usdc_amount

        if token_id in self.positions:
            pos       = self.positions[token_id]
            new_size  = pos["size"] + size
            avg_price = (pos["size"] * pos["entry_price"] + size * price) / new_size
            self.positions[token_id] = {"size": round(new_size, 4), "entry_price": round(avg_price, 4)}
        else:
            self.positions[token_id] = {"size": size, "entry_price": price}

        trade = {
            "time":    datetime.now().isoformat(timespec="seconds"),
            "side":    "BUY",
            "token":   token_id[:16] + "…",
            "size":    size,
            "price":   price,
            "usdc":    round(usdc_amount, 2),
            "balance": round(self.balance, 2),
        }
        self.trades.append(trade)
        log.info(
            f"[PAPER] ✅ BUY  {size:.4f} shares @ {price:.4f} "
            f"(${usdc_amount:.2f}) │ баланс: ${self.balance:.2f}"
        )
        return {"status": "filled", **trade}

    def sell(self, token_id: str, size: float) -> dict:
        price = self.get_midpoint(token_id)
        pos   = self.positions.get(token_id)

        if not pos or pos["size"] < size - 0.0001:
            log.warning(f"[PAPER] ❌ SELL отхвърлен — няма позиция за {token_id[:16]}…")
            return {"status": "rejected", "reason": "no_position"}

        usdc_received = round(size * price, 2)
        pnl           = round((price - pos["entry_price"]) * size, 4)
        self.balance += usdc_received

        remaining = round(pos["size"] - size, 4)
        if remaining < 0.0001:
            del self.positions[token_id]
        else:
            self.positions[token_id]["size"] = remaining

        trade = {
            "time":    datetime.now().isoformat(timespec="seconds"),
            "side":    "SELL",
            "token":   token_id[:16] + "…",
            "size":    round(size, 4),
            "price":   price,
            "usdc":    usdc_received,
            "pnl":     pnl,
            "balance": round(self.balance, 2),
        }
        self.trades.append(trade)
        log.info(
            f"[PAPER] ✅ SELL {size:.4f} shares @ {price:.4f} "
            f"(${usdc_received:.2f}) │ PnL: ${pnl:+.4f} │ баланс: ${self.balance:.2f}"
        )
        return {"status": "filled", **trade}

    # Stub-ове — съвместими с PolymarketClient интерфейса
    def limit_buy(self, token_id: str, price: float, size: float) -> dict:
        return self.buy(token_id, price * size)

    def limit_sell(self, token_id: str, price: float, size: float) -> dict:
        return self.sell(token_id, size)

    def cancel_all(self):
        log.info("[PAPER] cancel_all() — няма реални ордери.")

    def get_positions(self) -> list:
        return [{"token_id": k, **v} for k, v in self.positions.items()]

    # ── Резюме ──────────────────────────────────────────────────────────
    def summary(self):
        buys      = [t for t in self.trades if t["side"] == "BUY"]
        sells     = [t for t in self.trades if t["side"] == "SELL"]
        total_pnl = sum(t.get("pnl", 0) for t in sells)
        net_pnl   = self.balance - self._start

        log.info("╔══════════════════════════════════════╗")
        log.info("║       PAPER TRADING  РЕЗЮМЕ          ║")
        log.info("╠══════════════════════════════════════╣")
        log.info(f"║  Начален баланс : ${self._start:>10.2f}          ║")
        log.info(f"║  Краен баланс   : ${self.balance:>10.2f}          ║")
        log.info(f"║  Net PnL        : ${net_pnl:>+10.2f}          ║")
        log.info(f"║  Реализиран PnL : ${total_pnl:>+10.4f}          ║")
        log.info(f"║  Сделки BUY     : {len(buys):>4}                  ║")
        log.info(f"║  Сделки SELL    : {len(sells):>4}                  ║")
        log.info(f"║  Отворени поз.  : {len(self.positions):>4}                  ║")
        log.info("╚══════════════════════════════════════╝")
