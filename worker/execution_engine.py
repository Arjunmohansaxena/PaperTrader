"""Core limit-order processing: given the shared DB and a price-fetch
function, figure out which pending orders are triggered and execute them.

Deliberately separate from worker.py's infinite sleep-loop so this can be
called once per cycle and unit-tested directly (see
tests/test_limit_order_execution.py), without needing to run or mock a
real time.sleep loop.
"""

import logging
from datetime import datetime

logger = logging.getLogger("papertrader.worker")


def run_cycle(db_manager, limit_order_repo, get_price_fn) -> dict:
    """Runs one full worker cycle:
      1. find every symbol with at least one pending order
      2. fetch that symbol's current price ONCE (never once per order --
         see the worker context doc's Finnhub rate-limit guidance)
      3. evaluate and execute every pending order for that symbol that the
         new price triggers

    A failure fetching one symbol's price, or executing one order, is
    logged and skipped -- it never aborts the rest of the cycle, per the
    "an individual order/API failure must not kill the worker" requirement.
    Returns a small summary dict, useful for logging and for tests.
    """
    summary = {
        "symbols_checked": 0,
        "orders_evaluated": 0,
        "orders_executed": 0,
        "orders_failed": 0,
        "errors": [],
    }

    try:
        symbols = limit_order_repo.get_pending_symbols()
    except Exception as exc:
        logger.error("Could not load pending symbols: %s", exc)
        summary["errors"].append(str(exc))
        return summary

    for symbol in symbols:
        summary["symbols_checked"] += 1

        try:
            current_price = float(get_price_fn(symbol))
        except Exception as exc:
            logger.warning("Skipping %s this cycle -- could not get a price: %s", symbol, exc)
            summary["errors"].append(f"{symbol}: {exc}")
            continue

        try:
            orders = limit_order_repo.get_pending_by_symbol(symbol)
        except Exception as exc:
            logger.error("Could not load pending orders for %s: %s", symbol, exc)
            summary["errors"].append(f"{symbol}: {exc}")
            continue

        for order in orders:
            summary["orders_evaluated"] += 1
            if not order.is_triggered(current_price):
                continue

            try:
                executed = execute_order(db_manager, order, current_price)
            except Exception as exc:
                # A single order's unexpected failure must never take down
                # the worker or block other orders/symbols this cycle.
                logger.error("Order %s raised while executing: %s", order.order_id, exc)
                summary["errors"].append(f"order {order.order_id}: {exc}")
                continue

            if executed:
                summary["orders_executed"] += 1
                logger.info(
                    "Executed order %s: %s %s x%s @ %.2f",
                    order.order_id, order.side, order.symbol, order.quantity, current_price,
                )
            else:
                summary["orders_failed"] += 1

    return summary


def execute_order(db_manager, order, current_price: float) -> bool:
    """Executes exactly one triggered limit order as a single atomic
    transaction (balance update + holdings update + transaction record +
    order status, all together or all rolled back).

    Re-checks and row-locks the order's status as the first statement
    inside the transaction, so a duplicate cycle, a second worker
    instance, or the user cancelling the order through the app can never
    cause a double-execution -- whichever caller gets there first wins,
    and everyone else sees it's no longer PENDING and backs off cleanly.

    Returns True if it executed, False if it failed a validation check
    (insufficient funds/shares by the time it was locked, order already
    resolved) and was marked FAILED or skipped instead -- both are
    "handled" outcomes. Only a genuinely unexpected error propagates.
    """
    with db_manager.transaction() as tx:
        row = tx.fetch_one(
            "SELECT status FROM limit_orders WHERE order_id = ? FOR UPDATE",
            (order.order_id,),
        )
        if row is None or row[0] != "PENDING":
            return False  # already executed/cancelled since we loaded it -- not an error

        if order.side == "buy":
            return _execute_buy(tx, order, current_price)
        return _execute_sell(tx, order, current_price)


def _execute_buy(tx, order, price: float) -> bool:
    total_cost = order.quantity * price

    balance_row = tx.fetch_one("SELECT balance FROM users WHERE user_id = ? FOR UPDATE", (order.user_id,))
    if balance_row is None:
        _mark_failed(tx, order.order_id, "User account not found.")
        return False
    balance = balance_row[0]

    if total_cost > balance:
        _mark_failed(
            tx, order.order_id,
            f"Insufficient cash balance at execution time: needs {total_cost:.2f}, has {balance:.2f}.",
        )
        return False

    tx.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_cost, order.user_id))

    holding_row = tx.fetch_one(
        "SELECT quantity, avg_buy_price FROM holdings WHERE user_id = ? AND stock_name = ? FOR UPDATE",
        (order.user_id, order.symbol),
    )
    if holding_row is None:
        tx.execute(
            "INSERT INTO holdings (user_id, stock_name, quantity, avg_buy_price) VALUES (?, ?, ?, ?)",
            (order.user_id, order.symbol, order.quantity, price),
        )
    else:
        existing_qty, existing_avg = holding_row
        new_qty = existing_qty + order.quantity
        # Same weighted-average formula as models.position.Position.add_share.
        new_avg = (existing_avg * existing_qty + price * order.quantity) / new_qty
        tx.execute(
            "UPDATE holdings SET quantity = ?, avg_buy_price = ? WHERE user_id = ? AND stock_name = ?",
            (new_qty, new_avg, order.user_id, order.symbol),
        )

    _record_transaction(tx, order, price, "BUY")
    _mark_executed(tx, order.order_id, price)
    return True


def _execute_sell(tx, order, price: float) -> bool:
    holding_row = tx.fetch_one(
        "SELECT quantity, avg_buy_price FROM holdings WHERE user_id = ? AND stock_name = ? FOR UPDATE",
        (order.user_id, order.symbol),
    )
    if holding_row is None or holding_row[0] < order.quantity:
        held = holding_row[0] if holding_row else 0
        _mark_failed(
            tx, order.order_id,
            f"Insufficient shares at execution time: needs {order.quantity}, has {held}.",
        )
        return False

    existing_qty, _existing_avg = holding_row
    remaining = existing_qty - order.quantity
    if remaining == 0:
        tx.execute("DELETE FROM holdings WHERE user_id = ? AND stock_name = ?", (order.user_id, order.symbol))
    else:
        # Same as models.position.Position.remove_share: avg_buy_price is
        # unaffected by a sell, only quantity changes.
        tx.execute(
            "UPDATE holdings SET quantity = ? WHERE user_id = ? AND stock_name = ?",
            (remaining, order.user_id, order.symbol),
        )

    proceeds = order.quantity * price
    tx.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (proceeds, order.user_id))

    _record_transaction(tx, order, price, "SELL")
    _mark_executed(tx, order.order_id, price)
    return True


def _record_transaction(tx, order, price: float, transaction_type: str):
    tx.execute(
        "INSERT INTO transactions (user_id, stock_name, transaction_type, quantity, price, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (order.user_id, order.symbol, transaction_type, order.quantity, price, datetime.now()),
    )


def _mark_executed(tx, order_id: int, price: float):
    tx.execute(
        "UPDATE limit_orders SET status = 'EXECUTED', executed_price = ?, executed_at = ? WHERE order_id = ?",
        (price, datetime.now(), order_id),
    )


def _mark_failed(tx, order_id: int, reason: str):
    tx.execute(
        "UPDATE limit_orders SET status = 'FAILED', failure_reason = ? WHERE order_id = ?",
        (reason, order_id),
    )
