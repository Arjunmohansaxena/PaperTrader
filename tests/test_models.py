import unittest
from datetime import datetime

from models.portfolio import Portfolio
from models.position import Position
from models.transaction import Transaction
from models.user import User


class ModelTests(unittest.TestCase):
    def test_position_and_portfolio_work_together(self):
        position = Position("AAPL", 5, 100.0)
        position.add_share(3, 110.0)

        self.assertEqual(position.quantity, 8)
        self.assertAlmostEqual(position.avg_buy_price, 103.75)

        portfolio = Portfolio(1000.0)
        portfolio.buy_stock("AAPL", 2, 105.0)
        self.assertEqual(portfolio.positions["AAPL"].quantity, 2)
        self.assertAlmostEqual(portfolio.cash_balance, 790.0)

        portfolio.sell_stock("AAPL", 1, 110.0)
        self.assertEqual(portfolio.positions["AAPL"].quantity, 1)
        self.assertAlmostEqual(portfolio.cash_balance, 900.0)

    def test_user_password_handling(self):
        user = User(username="alice", email="alice@example.com", password="secret123")
        self.assertTrue(user.verify_password("secret123"))
        self.assertFalse(user.verify_password("wrong"))

    def test_transaction_total_amount(self):
        timestamp = datetime(2026, 7, 12, 10, 30, 0)
        transaction = Transaction(symbol="AAPL", side="buy", quantity=10, price=150.25, timestamp=timestamp)
        self.assertEqual(transaction.total_amount, 1502.5)


if __name__ == "__main__":
    unittest.main()
