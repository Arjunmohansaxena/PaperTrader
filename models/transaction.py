from datetime import datetime


class Transaction:
    def __init__(self, symbol: str, side: str, quantity: int, price: float, timestamp: datetime):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp
        self.total_amount = self.quantity * self.price

