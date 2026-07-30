"""Background worker: monitors pending limit orders and executes them once
the market price crosses the limit price.

Run directly:
    python worker/worker.py

This is a standalone process -- it is NOT a Flask app and exposes no HTTP
routes. It runs independently (e.g. on its own VM, managed by systemd for
auto-restart) and communicates with the Flask app only through the shared
Postgres database, never directly.
"""

import logging
import os
import signal
import sys
import time

# Allow `python worker/worker.py` to be run directly (from any working
# directory) while still importing project-root modules like
# `database.db_manager` the same way the rest of the app does.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager  # noqa: E402
from repositories.limit_order_repository import LimitOrderRepository  # noqa: E402
from services.market_data_provider import _fetch_stock_quote  # noqa: E402
from worker.config import WORKER_INTERVAL_SECONDS  # noqa: E402
from worker.execution_engine import run_cycle  # noqa: E402

logging.basicConfig(
    level=os.getenv("WORKER_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("papertrader.worker")

_shutdown_requested = False


def _handle_shutdown_signal(signum, _frame):
    global _shutdown_requested
    logger.info("Received signal %s -- finishing current cycle, then shutting down.", signum)
    _shutdown_requested = True


def _get_price(symbol: str) -> float:
    """Always hits Finnhub directly rather than the Flask app's short TTL
    quote cache (services.market_data_provider.get_stock_quote) -- a limit
    order decision needs the freshest price available at evaluation time,
    not a copy that could be up to QUOTE_CACHE_TTL_SECONDS old. Called at
    most once per symbol per cycle (see execution_engine.run_cycle), which
    is what actually keeps this within Finnhub's rate limits -- not the
    cache."""
    return float(_fetch_stock_quote(symbol)["c"])


def main():
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)

    logger.info("Starting PaperTrader limit-order worker (interval=%ss).", WORKER_INTERVAL_SECONDS)

    db_manager = None
    limit_order_repo = None
    while not _shutdown_requested:
        try:
            if db_manager is None:
                db_manager = DatabaseManager()
                limit_order_repo = LimitOrderRepository(db_manager)

            summary = run_cycle(db_manager, limit_order_repo, _get_price)
            if summary["orders_executed"] or summary["orders_failed"] or summary["errors"]:
                logger.info("Cycle summary: %s", summary)

        except Exception as exc:
            # A DB connection drop, an unexpected exception anywhere in the
            # cycle, etc. must never kill the worker process -- log it,
            # drop the (possibly broken) connection so the next iteration
            # reconnects from scratch, and keep running.
            logger.error("Worker cycle failed unexpectedly: %s", exc, exc_info=True)
            if db_manager is not None:
                try:
                    db_manager.close()
                except Exception:
                    pass
            db_manager = None

        for _ in range(WORKER_INTERVAL_SECONDS):
            if _shutdown_requested:
                break
            time.sleep(1)

    if db_manager is not None:
        db_manager.close()
    logger.info("Worker stopped.")


if __name__ == "__main__":
    main()
