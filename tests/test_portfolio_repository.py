import os
import tempfile
import unittest
from datetime import datetime
 
from database.db_manager import DatabaseManager
from models.portfolio import Portfolio
from models.transaction import Transaction
from repositories.portfolio_repository import PortfolioRepository
 
 
class PortfolioRepositoryTests(unittest.TestCase):
    def test_save_and_reload_portfolio_and_transactions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "papertrader.db")
            schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
 
            with DatabaseManager(db_path) as db_manager:
                with open(schema_path) as schema_file:
                    db_manager.executescript(schema_file.read())
 
                repository = PortfolioRepository(db_manager)
 
                portfolio = Portfolio(1000.0)
                portfolio.buy_stock("AAPL", 2, 100.0)
                repository.save(portfolio, user_id=7)
 
                reloaded = repository.get_by_user_id(7)
                self.assertEqual(reloaded.cash_balance, portfolio.cash_balance)
                self.assertEqual(reloaded.positions["AAPL"].quantity, portfolio.positions["AAPL"].quantity)
                self.assertEqual(reloaded.positions["AAPL"].avg_buy_price, portfolio.positions["AAPL"].avg_buy_price)
 
                transaction = Transaction(symbol="AAPL", side="buy", quantity=2, price=100.0, timestamp=datetime(2026, 7, 12, 10, 0, 0))
                repository.record_transaction(7, transaction)
                history = repository.get_transaction_history(7)
 
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0].symbol, "AAPL")
                self.assertEqual(history[0].side, "buy")
                self.assertEqual(history[0].total_amount, 200.0)
 
 
if __name__ == "__main__":
    unittest.main()