"""
Polymarket CLOB client wrapper.
Документация: https://docs.polymarket.com/
pip install py-clob-client
"""
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, MarketOrderArgs
from py_clob_client.constants import POLYGON

log = logging.getLogger(__name__)


class PolymarketClient:
    HOST = "https://clob.polymarket.com"

    def __init__(self, private_key: str):
        self.client = ClobClient(
            host=self.HOST,
            key=private_key,
            chain_id=POLYGON,
        )
        self.client.set_api_creds(self.client.create_or_derive_api_creds())
        log.info("Polymarket client инициализиран.")

    # ------------------------------------------------------------------ #
    #  Пазарни данни                                                       #
    # ------------------------------------------------------------------ #
    def get_midpoint(self, token_id: str) -> float:
        """Midpoint = (best_bid + best_ask) / 2 ≈ implied вероятност."""
        book = self.client.get_order_book(token_id)
        best_bid = float(book.bids[0].price) if book.bids else 0.0
        best_ask = float(book.asks[0].price) if book.asks else 1.0
        return (best_bid + best_ask) / 2

    def get_spread(self, token_id: str) -> float:
        """Bid-ask spread — по-голям спред = по-малко ликвидност."""
        book = self.client.get_order_book(token_id)
        if not book.bids or not book.asks:
            return 1.0
        return float(book.asks[0].price) - float(book.bids[0].price)

    def get_market(self, condition_id: str) -> dict:
        return self.client.get_market(condition_id)

    # ------------------------------------------------------------------ #
    #  Изпълнение на ордери                                                #
    # ------------------------------------------------------------------ #
    def buy(self, token_id: str, usdc_amount: float) -> dict:
        """Market buy — купи shares за USDC."""
        price = self.get_midpoint(token_id)
        size  = round(usdc_amount / price, 2)
        order = MarketOrderArgs(token_id=token_id, amount=usdc_amount)
        signed = self.client.create_market_order(order)
        resp   = self.client.post_order(signed)
        log.info(f"BUY {size:.2f} shares @ {price:.3f} | resp: {resp}")
        return resp

    def sell(self, token_id: str, size: float) -> dict:
        """Market sell — продай size shares."""
        price = self.get_midpoint(token_id)
        order = MarketOrderArgs(token_id=token_id, amount=size * price)
        signed = self.client.create_market_order(order)
        resp   = self.client.post_order(signed)
        log.info(f"SELL {size:.2f} shares @ {price:.3f} | resp: {resp}")
        return resp

    def limit_buy(self, token_id: str, price: float, size: float) -> dict:
        """Limit buy — по-добра цена, по-бавно изпълнение."""
        order  = OrderArgs(token_id=token_id, price=price, size=size, side="BUY")
        signed = self.client.create_order(order)
        return self.client.post_order(signed)

    def limit_sell(self, token_id: str, price: float, size: float) -> dict:
        order  = OrderArgs(token_id=token_id, price=price, size=size, side="SELL")
        signed = self.client.create_order(order)
        return self.client.post_order(signed)

    # ------------------------------------------------------------------ #
    #  Позиции                                                             #
    # ------------------------------------------------------------------ #
    def get_positions(self) -> list:
        return self.client.get_positions()

    def cancel_all(self):
        return self.client.cancel_all()
