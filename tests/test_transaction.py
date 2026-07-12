import unittest
from datetime import datetime

from models.transaction import Transaction


class TransactionTests(unittest.TestCase):
    def test_transaction_computes_total_amount(self):
        timestamp = datetime(2026, 7, 12, 10, 30, 0)
        transaction = Transaction(symbol="AAPL", side="buy", quantity=10, price=150.25, timestamp=timestamp)

        self.assertEqual(transaction.symbol, "AAPL")
        self.assertEqual(transaction.side, "buy")
        self.assertEqual(transaction.quantity, 10)
        self.assertEqual(transaction.price, 150.25)
        self.assertEqual(transaction.timestamp, timestamp)
        self.assertEqual(transaction.total_amount, 1502.5)


if __name__ == "__main__":
    unittest.main()
