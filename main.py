import os
import sys
from datetime import datetime

from database.db_manager import DatabaseManager
from repositories.portfolio_repository import PortfolioRepository
from repositories.user_repository import UserRepository
from models.portfolio import Portfolio
from models.transaction import Transaction
from services.market_data_provider import get_stock_price

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "database", "PaperTrader.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
STARTING_BALANCE = 100000.00


def ensure_schema(db_manager: DatabaseManager) -> None:
    with open(SCHEMA_PATH, "r") as schema_file:
        db_manager.executescript(schema_file.read())


def prompt_price(symbol: str) -> float:
    try:
        price = get_stock_price(symbol)
        print(f"  Current price for {symbol}: ${price:.2f}")
        return float(price)
    except Exception as exc:
        print(f"  Could not fetch a live price ({exc}).")
        while True:
            raw = input(f"  Enter a price for {symbol} manually: $").strip()
            try:
                return float(raw)
            except ValueError:
                print("  Please enter a valid number.")


def login_or_register(user_repo: UserRepository):
    while True:
        print("\n=== PaperTrader ===")
        print("1) Log in")
        print("2) Register")
        print("3) Quit")
        choice = input("> ").strip()

        if choice == "1":
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            user = user_repo.authenticate(username, password)
            if user:
                print(f"\nWelcome back, {user.username}!")
                return user
            print("Invalid username or password.")

        elif choice == "2":
            username = input("Choose a username: ").strip()
            email = input("Email: ").strip()
            password = input("Choose a password: ").strip()
            try:
                user = user_repo.create_user(username, email, password)
            except ValueError as exc:
                print(f"Error: {exc}")
                continue
            portfolio_repo = PortfolioRepository(user_repo.db_manager)
            portfolio_repo.save(Portfolio(cash_balance=STARTING_BALANCE), user.user_id)
            print(f"\nAccount created for {user.username} with ${STARTING_BALANCE:,.2f} starting cash.")
            print("Please log in.")

        elif choice == "3":
            sys.exit(0)

        else:
            print("Invalid option.")


def show_portfolio(portfolio: Portfolio) -> None:
    print(f"\nCash balance: ${portfolio.cash_balance:,.2f}")
    if not portfolio.positions:
        print("No open positions.")
        return

    print(f"{'Symbol':<8}{'Qty':>8}{'Avg Price':>14}{'Current':>14}{'Unrealized P/L':>18}")
    prices = {}
    for symbol, position in portfolio.positions.items():
        try:
            price = get_stock_price(symbol)
        except Exception:
            price = position.avg_buy_price
        prices[symbol] = price
        pnl = position.unrealized_profit_loss(price)
        print(f"{symbol:<8}{position.quantity:>8}{position.avg_buy_price:>14.2f}{price:>14.2f}{pnl:>18.2f}")

    total_value = portfolio.get_portfolio_value(prices)
    print(f"\nTotal portfolio value (cash + holdings): ${total_value:,.2f}")


def buy_flow(portfolio: Portfolio, portfolio_repo: PortfolioRepository, user_id: int) -> None:
    symbol = input("Symbol to buy: ").strip().upper()
    try:
        quantity = int(input("Quantity: ").strip())
    except ValueError:
        print("Quantity must be a whole number.")
        return
    if quantity <= 0:
        print("Quantity must be positive.")
        return

    price = prompt_price(symbol)
    try:
        portfolio.buy_stock(symbol, quantity, price)
    except ValueError as exc:
        print(f"Trade failed: {exc}")
        return

    portfolio_repo.save(portfolio, user_id)
    transaction = Transaction(symbol=symbol, side="buy", quantity=quantity, price=price, timestamp=datetime.now())
    portfolio_repo.record_transaction(user_id, transaction)
    print(f"Bought {quantity} {symbol} @ ${price:.2f}.")


def sell_flow(portfolio: Portfolio, portfolio_repo: PortfolioRepository, user_id: int) -> None:
    symbol = input("Symbol to sell: ").strip().upper()
    try:
        quantity = int(input("Quantity: ").strip())
    except ValueError:
        print("Quantity must be a whole number.")
        return
    if quantity <= 0:
        print("Quantity must be positive.")
        return

    price = prompt_price(symbol)
    try:
        portfolio.sell_stock(symbol, quantity, price)
    except ValueError as exc:
        print(f"Trade failed: {exc}")
        return

    portfolio_repo.save(portfolio, user_id)
    transaction = Transaction(symbol=symbol, side="sell", quantity=quantity, price=price, timestamp=datetime.now())
    portfolio_repo.record_transaction(user_id, transaction)
    print(f"Sold {quantity} {symbol} @ ${price:.2f}.")


def show_history(portfolio_repo: PortfolioRepository, user_id: int) -> None:
    history = portfolio_repo.get_transaction_history(user_id)
    if not history:
        print("\nNo transactions yet.")
        return
    print(f"\n{'Timestamp':<20}{'Side':<6}{'Symbol':<8}{'Qty':>6}{'Price':>12}{'Total':>14}")
    for txn in history:
        timestamp = txn.timestamp
        stamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, datetime) else str(timestamp)[:19]
        print(f"{stamp_str:<20}{txn.side:<6}{txn.symbol:<8}{txn.quantity:>6}{txn.price:>12.2f}{txn.total_amount:>14.2f}")


def main_menu(user, portfolio_repo: PortfolioRepository) -> None:
    while True:
        portfolio = portfolio_repo.get_by_user_id(user.user_id)
        print(f"\n=== {user.username}'s Portfolio ===")
        print("1) View portfolio")
        print("2) Buy stock")
        print("3) Sell stock")
        print("4) Transaction history")
        print("5) Log out")
        choice = input("> ").strip()

        if choice == "1":
            show_portfolio(portfolio)
        elif choice == "2":
            buy_flow(portfolio, portfolio_repo, user.user_id)
        elif choice == "3":
            sell_flow(portfolio, portfolio_repo, user.user_id)
        elif choice == "4":
            show_history(portfolio_repo, user.user_id)
        elif choice == "5":
            return
        else:
            print("Invalid option.")


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with DatabaseManager(DB_PATH) as db_manager:
        ensure_schema(db_manager)
        user_repo = UserRepository(db_manager)
        portfolio_repo = PortfolioRepository(db_manager)

        while True:
            user = login_or_register(user_repo)
            main_menu(user, portfolio_repo)


if __name__ == "__main__":
    main()
