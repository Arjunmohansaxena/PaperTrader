from database.db_manager import DatabaseManager
from models.limit_order import LimitOrder


class LimitOrderRepository:
    """CRUD for limit_orders. Both the Flask app (placing/cancelling/listing
    a user's orders) and the worker (reading pending orders) use this --
    Postgres is the single shared source of truth between the two
    processes, per the worker context doc's architecture.

    Deliberately NOT included here: any method that executes an order.
    That mutation (balance + holdings + transaction + order status, all
    atomically) is handled by worker/execution_engine.py directly through
    DatabaseManager.transaction(), because this repo's create/cancel
    methods use the auto-committing DatabaseManager.execute() -- fine for
    a single-row write, but unable to express the "all four writes land
    together or none do" guarantee order execution needs.
    """

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db_manager = db_manager if db_manager is not None else DatabaseManager()

    def create_order(self, user_id: int, symbol: str, side: str, quantity: int, limit_price: float) -> LimitOrder:
        symbol = symbol.strip().upper()
        side = side.strip().upper()
        row = self.db_manager.fetch_one(
            "INSERT INTO limit_orders (user_id, stock_name, side, quantity, limit_price) "
            "VALUES (?, ?, ?, ?, ?) RETURNING order_id, created_at",
            (user_id, symbol, side, quantity, limit_price),
        )
        return LimitOrder(
            order_id=row[0], user_id=user_id, symbol=symbol, side=side,
            quantity=quantity, limit_price=limit_price, status="PENDING", created_at=row[1],
        )

    def get_by_id(self, order_id: int) -> LimitOrder | None:
        row = self.db_manager.fetch_one(
            "SELECT order_id, user_id, stock_name, side, quantity, limit_price, status, "
            "executed_price, failure_reason, created_at, executed_at "
            "FROM limit_orders WHERE order_id = ?",
            (order_id,),
        )
        return self._row_to_order(row) if row else None

    def get_by_user_id(self, user_id: int) -> list[LimitOrder]:
        rows = self.db_manager.fetch_all(
            "SELECT order_id, user_id, stock_name, side, quantity, limit_price, status, "
            "executed_price, failure_reason, created_at, executed_at "
            "FROM limit_orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [self._row_to_order(row) for row in rows]

    def get_pending_symbols(self) -> list[str]:
        """Distinct symbols with at least one pending order -- lets the
        worker fetch one price per symbol per cycle instead of one per
        order, per the worker context doc's rate-limit guidance."""
        rows = self.db_manager.fetch_all(
            "SELECT DISTINCT stock_name FROM limit_orders WHERE status = 'PENDING'"
        )
        return [row[0] for row in rows]

    def get_pending_by_symbol(self, symbol: str) -> list[LimitOrder]:
        rows = self.db_manager.fetch_all(
            "SELECT order_id, user_id, stock_name, side, quantity, limit_price, status, "
            "executed_price, failure_reason, created_at, executed_at "
            "FROM limit_orders WHERE status = 'PENDING' AND stock_name = ? "
            "ORDER BY created_at ASC",
            (symbol.strip().upper(),),
        )
        return [self._row_to_order(row) for row in rows]

    def cancel(self, order_id: int, user_id: int) -> bool:
        """Cancels a still-pending order belonging to user_id. Returns
        False (no-op) if it's already executed/cancelled/failed, or
        doesn't belong to this user -- callers shouldn't be able to cancel
        someone else's order or "un-cancel" a resolved one."""
        cursor = self.db_manager.execute(
            "UPDATE limit_orders SET status = 'CANCELLED' "
            "WHERE order_id = ? AND user_id = ? AND status = 'PENDING'",
            (order_id, user_id),
        )
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_order(row) -> LimitOrder:
        return LimitOrder(
            order_id=row[0], user_id=row[1], symbol=row[2], side=row[3],
            quantity=row[4], limit_price=row[5], status=row[6],
            executed_price=row[7], failure_reason=row[8],
            created_at=row[9], executed_at=row[10],
        )
