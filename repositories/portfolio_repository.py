from database.db_manager import DatabaseManager
from models.portfolio import Portfolio
from models.position import Position
from models.transaction import Transaction

def  get_user_portfolio(user_id: int) -> Portfolio | None:
    db_manager = DatabaseManager()  # Initialize the database manager
    portfolio_row = db_manager.fetch_one(
        "SELECT * FROM portfolios WHERE user_id = ?", (user_id,)
    )
    if portfolio_row:
        portfolio = Portfolio(cash_balance=portfolio_row["cash_balance"])
        positions_rows = db_manager.fetch_all(
            "SELECT * FROM positions WHERE user_id = ?", (user_id,)
        )
        for pos_row in positions_rows:
            position = Position(
                symbol=pos_row["symbol"],
                quantity=pos_row["quantity"],
                avg_buy_price=pos_row["avg_buy_price"]
            )
            portfolio.positions[position.symbol] = position
        return portfolio
    return None

def save_user_portfolio(user_id: int, portfolio: Portfolio):
    db_manager = DatabaseManager()  # Initialize the database manager
    db_manager.execute(
        "INSERT OR REPLACE INTO holdings (user_id, cash_balance) VALUES (?, ?)",
        (user_id, portfolio.cash_balance),
    )
    for position in portfolio.positions.values():
        db_manager.execute(
            "INSERT OR REPLACE INTO holdings (user_id, symbol, quantity, avg_buy_price) VALUES (?, ?, ?, ?)",
            (user_id, position.symbol, position.quantity, position.avg_buy_price),
        )

def record_user_transaction(user_id: int, transaction: Transaction):
    db_manager = DatabaseManager()  # Initialize the database manager
    db_manager.execute(
        "INSERT INTO transactions (user_id, symbol, side, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, transaction.symbol, transaction.side, transaction.quantity, transaction.price, transaction.timestamp),
    )
    save_user_portfolio(user_id, get_user_portfolio(user_id))  # Update the portfolio after recording the transaction

def get_user_transaction_history(user_id: int) -> list[Transaction]:
    db_manager = DatabaseManager()  # Initialize the database manager
    transactions_rows = db_manager.fetch_all(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,)
    )
    transactions = []
    for row in transactions_rows:
        transaction = Transaction(
            symbol=row["symbol"],
            side=row["side"],
            quantity=row["quantity"],
            price=row["price"],
            timestamp=row["timestamp"]
        )
        transactions.append(transaction)
    return transactions