import json
import threading
import time

import websocket

from services.market_data_provider import FINNHUB_API_KEY

RECONNECT_DELAY_SECONDS = 3
SUBSCRIPTION_SYNC_INTERVAL_SECONDS = 5


class FinnhubPriceStream:
    """Streams live trade prices from Finnhub WebSocket."""

    def __init__(self, get_symbols, on_prices):
        self._get_symbols = get_symbols
        self._on_prices = on_prices
        self._ws = None
        self._subscribed: set[str] = set()
        self._lock = threading.Lock()

    def start(self):
        if not FINNHUB_API_KEY:
            return
        threading.Thread(target=self._run_forever, daemon=True).start()
        threading.Thread(target=self._sync_subscriptions_loop, daemon=True).start()

    def _run_forever(self):
        while True:
            ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}",
                on_message=self._on_message,
                on_open=self._on_open,
            )
            with self._lock:
                self._ws = ws
                self._subscribed.clear()
            ws.run_forever(ping_interval=30, ping_timeout=10)
            time.sleep(RECONNECT_DELAY_SECONDS)

    def _on_open(self, ws):
        self._sync_subscriptions(ws)

    def _on_message(self, ws, message):
        payload = json.loads(message)
        if payload.get("type") != "trade":
            return

        updates = {}
        for trade in payload.get("data", []):
            updates[trade["s"]] = float(trade["p"])

        if updates:
            self._on_prices(updates)

    def _sync_subscriptions_loop(self):
        while True:
            time.sleep(SUBSCRIPTION_SYNC_INTERVAL_SECONDS)
            with self._lock:
                ws = self._ws
            if ws and ws.sock and ws.sock.connected:
                self._sync_subscriptions(ws)

    def _sync_subscriptions(self, ws):
        wanted = set(self._get_symbols())

        for symbol in wanted - self._subscribed:
            ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
            self._subscribed.add(symbol)

        for symbol in self._subscribed - wanted:
            ws.send(json.dumps({"type": "unsubscribe", "symbol": symbol}))
            self._subscribed.discard(symbol)
