import atexit
import os
from datetime import datetime
from functools import wraps

from flask_socketio import SocketIO, emit
from flask import jsonify 
from flask import Flask, flash, redirect, render_template, request, session, url_for

from database.db_manager import DatabaseManager
from models.portfolio import Portfolio
from models.transaction import Transaction
from repositories.portfolio_repository import PortfolioRepository
from repositories.user_repository import UserRepository
from repositories.watchlist_repository import WatchlistRepository
from services.finnhub_stream import FinnhubPriceStream
from services.market_data_provider import get_stock_price, get_stock_symbol, search_stock
from utils.exceptions import StockNotFoundError

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "database", "PaperTrader.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
STARTING_BALANCE = 100000.00

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = os.environ.get("PAPERTRADER_SECRET_KEY", "dev-secret-key-change-me")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
db_manager = DatabaseManager(DB_PATH)
with open(SCHEMA_PATH) as schema_file:
    db_manager.executescript(schema_file.read())
atexit.register(db_manager.close)

user_repo = UserRepository(db_manager)
portfolio_repo = PortfolioRepository(db_manager)
watchlist_repo = WatchlistRepository(db_manager)


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return user_repo.get_by_id(user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def resolve_price(symbol: str, manual_price: str):
    """Returns (price, error_needs_manual_entry)."""
    if manual_price:
        try:
            return float(manual_price), None
        except ValueError:
            return None, "Manual price must be a number."
    try:
        return float(get_stock_price(symbol)), None
    except Exception as exc:
        return None, f"Could not fetch a live price for {symbol}: {exc}"


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html", username=username, email=email)

        try:
            user = user_repo.create_user(username, email, password)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("register.html", username=username, email=email)

        portfolio_repo.save(Portfolio(cash_balance=STARTING_BALANCE), user.user_id)
        flash(f"Account created for {user.username} with ${STARTING_BALANCE:,.2f} starting cash. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_credentials = request.form.get("user_credentials", "").strip()
        password = request.form.get("password", "")

        user = user_repo.authenticate(user_credentials, password)

        if user:
            session["user_id"] = user.user_id
            session["username"] = user.username
            flash(f"Welcome back, {user.username}.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")
        return render_template(
            "login.html",
            user_credentials=user_credentials
        )

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    portfolio = portfolio_repo.get_by_user_id(user.user_id)

    rows = []
    holdings_value = 0.0
    for symbol, position in sorted(portfolio.positions.items()):
        try:
            price = float(get_stock_price(symbol))
            live = True
        except Exception:
            price = position.avg_buy_price
            live = False
        pnl = position.unrealized_profit_loss(price)
        rows.append(
            {
                "symbol": symbol,
                "quantity": position.quantity,
                "avg_price": position.avg_buy_price,
                "current_price": price,
                "pnl": pnl,
                "live": live,
            }
        )
        holdings_value += price * position.quantity

    total_value = portfolio.cash_balance + holdings_value
    
    # Get watchlists and recent transaction history
    watchlists = watchlist_repo.get_by_user_id(user.user_id)
    transactions = portfolio_repo.get_transaction_history(user.user_id)[:3]
    
    return render_template(
        "dashboard.html",
        user=user,
        portfolio=portfolio,
        rows=rows,
        total_value=total_value,
        watchlists=watchlists,
        transactions=transactions,
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    user = current_user()
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        quantity_raw = request.form.get("quantity", "").strip()
        manual_price = request.form.get("manual_price", "").strip()

        try:
            quantity = int(quantity_raw)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive whole number.", "error")
            return render_template("buy.html", symbol=symbol, quantity=quantity_raw)

        price, error = resolve_price(symbol, manual_price)
        if error:
            flash(error, "error")
            return render_template("buy.html", symbol=symbol, quantity=quantity_raw, need_manual_price=True)

        portfolio = portfolio_repo.get_by_user_id(user.user_id)
        try:
            portfolio.buy_stock(symbol, quantity, price)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("buy.html", symbol=symbol, quantity=quantity_raw)

        portfolio_repo.save(portfolio, user.user_id)
        transaction = Transaction(symbol=symbol, side="buy", quantity=quantity, price=price, timestamp=datetime.now())
        portfolio_repo.record_transaction(user.user_id, transaction)
        flash(f"Bought {quantity} {symbol} @ ${price:.2f}.", "success")
        return redirect(url_for("dashboard"))

    return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    user = current_user()
    if request.method == "POST":
        symbol = request.form.get("symbol", "").strip().upper()
        quantity_raw = request.form.get("quantity", "").strip()
        manual_price = request.form.get("manual_price", "").strip()

        try:
            quantity = int(quantity_raw)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive whole number.", "error")
            return render_template("sell.html", symbol=symbol, quantity=quantity_raw)

        price, error = resolve_price(symbol, manual_price)
        if error:
            flash(error, "error")
            return render_template("sell.html", symbol=symbol, quantity=quantity_raw, need_manual_price=True)

        portfolio = portfolio_repo.get_by_user_id(user.user_id)
        try:
            portfolio.sell_stock(symbol, quantity, price)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("sell.html", symbol=symbol, quantity=quantity_raw)

        portfolio_repo.save(portfolio, user.user_id)
        transaction = Transaction(symbol=symbol, side="sell", quantity=quantity, price=price, timestamp=datetime.now())
        portfolio_repo.record_transaction(user.user_id, transaction)
        flash(f"Sold {quantity} {symbol} @ ${price:.2f}.", "success")
        return redirect(url_for("dashboard"))

    return render_template("sell.html")


@app.route("/history")
@login_required
def history():
    user = current_user()
    transactions = portfolio_repo.get_transaction_history(user.user_id)
    return render_template("history.html", transactions=transactions)

@app.route("/api/search")
@login_required
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    try:
        results = search_stock(query)
    except Exception:
        results = []
    return jsonify(results)


@app.route("/watchlists")
@login_required
def watchlists_view():
    user = current_user()
    user_watchlists = watchlist_repo.get_by_user_id(user.user_id)
    
    watchlist_data = []
    for wl in user_watchlists:
        stocks_data = []
        for symbol in wl.stocks:
            try:
                price = float(get_stock_price(symbol))
                live = True
            except Exception:
                price = 0.0
                live = False
            stocks_data.append({"symbol": symbol, "price": price, "live": live})
        watchlist_data.append({
            "watch_list_id": wl.watch_list_id,
            "name": wl.name,
            "stocks": stocks_data
        })
        
    return render_template("watchlists.html", user=user, watchlists=watchlist_data)


@app.route("/watchlists/create", methods=["POST"])
@login_required
def create_watchlist():
    user = current_user()
    name = request.form.get("name", "").strip()
    if not name:
        flash("Watchlist name cannot be empty.", "error")
        return redirect(url_for("watchlists_view"))
    
    try:
        watchlist_repo.create_watchlist(user.user_id, name)
        flash(f"Watchlist '{name}' created successfully.", "success")
    except Exception as exc:
        flash(f"Error creating watchlist: {exc}", "error")
        
    return redirect(url_for("watchlists_view"))


@app.route("/watchlists/<int:watchlist_id>/add", methods=["POST"])
@login_required
def add_watchlist_stock(watchlist_id):
    raw_input_value = request.form.get("symbol", "").strip()
    symbol = raw_input_value.upper()
    if not symbol:
        flash("Symbol cannot be empty.", "error")
        return redirect(url_for("watchlists_view"))
        
    if " " in raw_input_value or len(raw_input_value) > 5:
        try:
            symbol = get_stock_symbol(raw_input_value)
        except StockNotFoundError as exc:
            flash(str(exc), "error")
            return redirect(url_for("watchlists_view"))
            
    user = current_user()
    wl = watchlist_repo.get_by_id(watchlist_id)
    if not wl or wl.user_id != user.user_id:
        flash("Watchlist not found.", "error")
        return redirect(url_for("watchlists_view"))
        
    try:
        get_stock_price(symbol)
    except Exception as exc:
        if "FINNHUB_API_KEY is not set" not in str(exc) and "No price found" in str(exc):
            flash(f"Stock '{symbol}' not found.", "error")
            return redirect(url_for("watchlists_view"))
            
    watchlist_repo.add_stock(watchlist_id, symbol)
    flash(f"Added {symbol} to watchlist '{wl.name}'.", "success")
    return redirect(url_for("watchlists_view"))


@app.route("/watchlists/<int:watchlist_id>/remove", methods=["POST"])
@login_required
def remove_watchlist_stock(watchlist_id):
    symbol = request.form.get("symbol", "").strip().upper()
    user = current_user()
    wl = watchlist_repo.get_by_id(watchlist_id)
    if not wl or wl.user_id != user.user_id:
        flash("Watchlist not found.", "error")
        return redirect(url_for("watchlists_view"))
        
    watchlist_repo.remove_stock(watchlist_id, symbol)
    flash(f"Removed {symbol} from watchlist '{wl.name}'.", "success")
    return redirect(url_for("watchlists_view"))


@app.route("/watchlists/<int:watchlist_id>/delete", methods=["POST"])
@login_required
def delete_watchlist(watchlist_id):
    user = current_user()
    wl = watchlist_repo.get_by_id(watchlist_id)
    if not wl or wl.user_id != user.user_id:
        flash("Watchlist not found.", "error")
        return redirect(url_for("watchlists_view"))
        
    watchlist_repo.delete(watchlist_id)
    flash(f"Deleted watchlist '{wl.name}'.", "success")
    return redirect(url_for("watchlists_view"))


REST_BOOTSTRAP_INTERVAL_SECONDS = 60


def _collect_tracked_symbols():
    symbols = set()
    for row in db_manager.fetch_all("SELECT DISTINCT stock_name FROM holdings"):
        symbols.add(row[0])
    for row in db_manager.fetch_all("SELECT DISTINCT stock_symbol FROM watchlist_stocks"):
        symbols.add(row[0])
    return symbols


_last_prices = {}


def _emit_price_updates(updates: dict):
    global _last_prices
    if not updates:
        return
    _last_prices.update(updates)
    socketio.emit("price_update", updates)


@socketio.on("connect")
def handle_connect():
    if _last_prices:
        emit("price_update", _last_prices)


def bootstrap_prices():
    """REST snapshot for initial load, after-hours, and when WebSocket is quiet."""
    symbols = _collect_tracked_symbols()
    if not symbols:
        return
    prices = {}
    for symbol in symbols:
        try:
            prices[symbol] = float(get_stock_price(symbol))
        except Exception:
            continue
    _emit_price_updates(prices)


def price_bootstrap_loop():
    while True:
        bootstrap_prices()
        socketio.sleep(REST_BOOTSTRAP_INTERVAL_SECONDS)


if __name__ == "__main__":
    socketio.start_background_task(price_bootstrap_loop)
    FinnhubPriceStream(_collect_tracked_symbols, _emit_price_updates).start()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)