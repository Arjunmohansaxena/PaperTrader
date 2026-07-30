class LimitOrder:
    """A pending (or resolved) buy/sell instruction that should execute once
    the market price crosses a limit price. side is lowercase ("buy"/"sell")
    to match the convention models.Transaction already uses; status is
    uppercase to match the schema's CHECK constraint."""

    def __init__(
        self,
        order_id: int | None,
        user_id: int,
        symbol: str,
        side: str,
        quantity: int,
        limit_price: float,
        status: str = "PENDING",
        executed_price: float | None = None,
        failure_reason: str | None = None,
        created_at=None,
        executed_at=None,
    ):
        self.order_id = order_id
        self.user_id = user_id
        self.symbol = symbol
        self.side = side.lower()
        self.quantity = quantity
        self.limit_price = limit_price
        self.status = status
        self.executed_price = executed_price
        self.failure_reason = failure_reason
        self.created_at = created_at
        self.executed_at = executed_at

    def is_triggered(self, current_price: float) -> bool:
        """BUY triggers when the price has fallen to/below the limit;
        SELL triggers when it has risen to/above the limit."""
        if self.side == "buy":
            return current_price <= self.limit_price
        if self.side == "sell":
            return current_price >= self.limit_price
        raise ValueError(f"Unknown limit order side: {self.side!r}")
