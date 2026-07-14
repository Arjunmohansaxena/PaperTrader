import os

from database.db_manager import DatabaseManager
from models.portfolio import Portfolio
from models.position import Position
from models.transaction import Transaction

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "PaperTrader.db")


class PortfolioRepository:
    def __init__(self, db_manager: DatabaseManager | None = None):
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            self.db_manager = DatabaseManager(DEFAULT_DB_PATH)

    def save(self, portfolio: Portfolio, user_id: int):
        self.db_manager.execute(
            "INSERT OR IGNORE INTO users (user_id, username, email, password_hash, balance) VALUES (?, ?, ?, ?, ?)",
            (user_id, f"user_{user_id}", f"user_{user_id}@example.com", "hash", portfolio.cash_balance),
        )
        self.db_manager.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (portfolio.cash_balance, user_id),
        )
        self.db_manager.execute(
            "DELETE FROM holdings WHERE user_id = ?",
            (user_id,),
        )
        for position in portfolio.positions.values():
            self.db_manager.execute(
                "INSERT OR REPLACE INTO holdings (user_id, stock_name, quantity, avg_buy_price) VALUES (?, ?, ?, ?)",
                (user_id, position.symbol, position.quantity, position.avg_buy_price),
            )

    def get_by_user_id(self, user_id: int) -> Portfolio | None:
        user_row = self.db_manager.fetch_one(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        )
        if user_row is None:
            return None

        portfolio = Portfolio(cash_balance=user_row[0])
        positions_rows = self.db_manager.fetch_all(
            "SELECT stock_name, quantity, avg_buy_price FROM holdings WHERE user_id = ?", (user_id,)
        )
        for row in positions_rows:
            position = Position(
                symbol=row[0],
                quantity=row[1],
                avg_buy_price=row[2],
            )
            portfolio.positions[position.symbol] = position
        return portfolio

    def record_transaction(self, user_id: int, transaction: Transaction):
        self.db_manager.execute(
            "INSERT INTO transactions (user_id, stock_name, transaction_type, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, transaction.symbol, transaction.side.upper(), transaction.quantity, transaction.price, transaction.timestamp),
        )
        self.save(self.get_by_user_id(user_id) or Portfolio(0.0), user_id)

    def get_transaction_history(self, user_id: int) -> list[Transaction]:
        transactions_rows = self.db_manager.fetch_all(
            "SELECT stock_name, transaction_type, quantity, price, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        )
        transactions = []
        for row in transactions_rows:
            transaction = Transaction(
                symbol=row[0],
                side=row[1].lower(),
                quantity=row[2],
                price=row[3],
                timestamp=row[4],
            )
            transactions.append(transaction)
        return transactions


def get_user_portfolio(user_id: int) -> Portfolio | None:
    repository = PortfolioRepository()
    return repository.get_by_user_id(user_id)


def save_user_portfolio(user_id: int, portfolio: Portfolio):
    repository = PortfolioRepository()
    repository.save(portfolio, user_id)


def record_user_transaction(user_id: int, transaction: Transaction):
    repository = PortfolioRepository()
    repository.record_transaction(user_id, transaction)


def get_user_transaction_history(user_id: int) -> list[Transaction]:
    repository = PortfolioRepository()
    return repository.get_transaction_history(user_id)
