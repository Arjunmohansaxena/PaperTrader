"""Portfolio metrics service.

Every number shown on the /portfolio page is computed here, in one place,
from the portfolio's current holdings plus its full transaction history.
Nothing here talks to Flask or Jinja — it just returns plain dicts/lists so
the route can render them and, later, the AI Portfolio Review can consume
the same structure instead of recomputing anything itself.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from services.market_data_provider import (
    get_stock_quote,
    get_company_profile,
    get_company_name,         \
    get_historical_prices,
)

# Matches the starting cash every new account is created with (see app.py).
STARTING_BALANCE = 100000.00

RANGE_LOOKBACK = {
    "1D": timedelta(days=1),
    "1W": timedelta(weeks=1),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "1Y": timedelta(days=365),
    "ALL": None,
}

# Sector and display name rarely change, so a simple in-process cache avoids
# re-hitting Finnhub's profile endpoint for every holding on every page load.
_profile_cache: dict[str, dict] = {}


def _parse_timestamp(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.now()


def _sorted_ascending(transactions):
    parsed = [(_parse_timestamp(txn.timestamp), txn) for txn in transactions]
    parsed.sort(key=lambda pair: pair[0])
    return parsed


def compute_realized_pnl(transactions) -> float:
    """Replays every trade in chronological order on an average-cost basis
    to work out total realized profit/loss across all sold shares. The app
    doesn't store this at sale time, so it has to be reconstructed here."""
    running: dict[str, list] = {}
    realized = 0.0

    for _, txn in _sorted_ascending(transactions):
        qty, avg_cost = running.get(txn.symbol, [0, 0.0])

        if txn.side == "buy":
            new_qty = qty + txn.quantity
            new_avg = ((avg_cost * qty) + (txn.price * txn.quantity)) / new_qty if new_qty else 0.0
            running[txn.symbol] = [new_qty, new_avg]
        elif txn.side == "sell":
            sell_qty = min(txn.quantity, qty) if qty else 0
            realized += (txn.price - avg_cost) * sell_qty
            running[txn.symbol] = [max(qty - txn.quantity, 0), avg_cost]

    return realized


def _profile_for_symbol(symbol: str) -> dict:
    if symbol in _profile_cache:
        return _profile_cache[symbol]
    try:
        profile = get_company_profile(symbol)
    except Exception:
        profile = {}
    _profile_cache[symbol] = profile
    return profile


def _sector_for_symbol(symbol: str) -> str:
    return _profile_for_symbol(symbol).get("finnhubIndustry") or "Unknown"


def _name_for_symbol(symbol: str) -> str:
    name = _profile_for_symbol(symbol).get("name")
    if name:
        return name
    fallback = get_company_name(symbol)
    return fallback or symbol


def compute_sector_allocation(position_values: dict, cash_balance: float, total_value: float) -> list:
    """position_values: {symbol: current_market_value}. Returns rows sorted
    by value, largest first, with a trailing Cash bucket."""
    sector_totals: dict[str, float] = defaultdict(float)
    for symbol, value in position_values.items():
        sector_totals[_sector_for_symbol(symbol)] += value

    rows = [
        {"sector": sector, "value": value, "pct": (value / total_value * 100) if total_value else 0.0}
        for sector, value in sector_totals.items()
    ]
    rows.sort(key=lambda r: r["value"], reverse=True)

    if cash_balance > 0:
        rows.append({
            "sector": "Cash",
            "value": cash_balance,
            "pct": (cash_balance / total_value * 100) if total_value else 0.0,
        })
    return rows


def compute_top_movers(holdings_rows: list):
    """Prefers today's live percent change; falls back to total return since
    purchase when no live quote is available. Returns (gainer, loser), each
    either a dict or None if there's nothing to compare."""
    candidates = [r for r in holdings_rows if r.get("day_change_pct") is not None]
    metric = "day_change_pct"
    if not candidates:
        candidates = [r for r in holdings_rows if r.get("return_pct") is not None]
        metric = "return_pct"
    if not candidates:
        return None, None

    gainer = max(candidates, key=lambda r: r[metric])
    loser = min(candidates, key=lambda r: r[metric])
    return (
        {"symbol": gainer["symbol"], "name": gainer["name"], "pct": gainer[metric], "basis": metric},
        {"symbol": loser["symbol"], "name": loser["name"], "pct": loser[metric], "basis": metric},
    )


def compute_portfolio_history(transactions, range_key: str) -> list:
    """Approximates portfolio value over time by replaying the transaction
    log (to get exact cash + share counts at each point in time) against
    historical closing prices (to value the shares held at that point)."""
    range_key = (range_key or "ALL").upper()
    asc = _sorted_ascending(transactions)
    if not asc:
        return []

    now = datetime.now()
    lookback = RANGE_LOOKBACK.get(range_key)
    start = asc[0][0] if lookback is None else max(asc[0][0], now - lookback)

    symbols = sorted({txn.symbol for _, txn in asc})

    price_series = {}
    for symbol in symbols:
        try:
            points = get_historical_prices(symbol, range_key)
        except Exception:
            points = []
        price_series[symbol] = [(datetime.fromtimestamp(p["timestamp"]), p["close"]) for p in points]

    timeline = sorted({ts for series in price_series.values() for ts, _ in series if ts >= start})
    if not timeline:
        return []

    def price_at(symbol, ts):
        latest = None
        for point_ts, close in price_series.get(symbol, []):
            if point_ts <= ts:
                latest = close
            else:
                break
        return latest

    pointer = 0
    cash = STARTING_BALANCE
    positions: dict[str, float] = defaultdict(float)
    history = []

    for ts in timeline:
        while pointer < len(asc) and asc[pointer][0] <= ts:
            _, txn = asc[pointer]
            if txn.side == "buy":
                cash -= txn.quantity * txn.price
                positions[txn.symbol] += txn.quantity
            else:
                cash += txn.quantity * txn.price
                positions[txn.symbol] -= txn.quantity
            pointer += 1

        holdings_value = 0.0
        for symbol, qty in positions.items():
            if qty <= 0:
                continue
            price = price_at(symbol, ts)
            if price is None:
                continue
            holdings_value += qty * price

        history.append({"timestamp": int(ts.timestamp()), "value": cash + holdings_value})

    return history


def get_portfolio_metrics(user_id, portfolio_repo) -> dict | None:
    """The single entry point the /portfolio route (and, later, the AI
    review) should call. Returns None if the user has no portfolio yet."""
    portfolio = portfolio_repo.get_by_user_id(user_id)
    if portfolio is None:
        return None

    transactions = portfolio_repo.get_transaction_history(user_id)

    quotes = {}
    for symbol in portfolio.positions:
        try:
            quotes[symbol] = get_stock_quote(symbol)
        except Exception:
            quotes[symbol] = None

    holdings_rows = []
    position_values: dict[str, float] = {}
    invested_capital = 0.0
    unrealized_pnl = 0.0

    for symbol, position in portfolio.positions.items():
        quote = quotes.get(symbol)
        price = float(quote["c"]) if quote else position.avg_buy_price
        cost_basis = position.quantity * position.avg_buy_price
        value = position.quantity * price
        pnl = position.unrealized_profit_loss(price)
        return_pct = (pnl / cost_basis * 100) if cost_basis else 0.0
        day_change_pct = float(quote["dp"]) if quote and quote.get("dp") is not None else None

        position_values[symbol] = value
        invested_capital += cost_basis
        unrealized_pnl += pnl

        holdings_rows.append({
            "symbol": symbol,
            "name": _name_for_symbol(symbol), 
            "quantity": position.quantity,
            "avg_cost": position.avg_buy_price,
            "current_price": price,
            "value": value,
            "pnl": pnl,
            "return_pct": return_pct,
            "day_change_pct": day_change_pct,
            "live": quote is not None,
        })

    holdings_rows.sort(key=lambda r: r["value"], reverse=True)

    holdings_value = sum(position_values.values())
    total_value = portfolio.cash_balance + holdings_value
    realized_pnl = compute_realized_pnl(transactions)
    total_return_pct = ((total_value - STARTING_BALANCE) / STARTING_BALANCE * 100) if STARTING_BALANCE else 0.0

    allocation_rows = [
        {
            "label": r["name"],
            "value": r["value"],
            "pct": (r["value"] / total_value * 100) if total_value else 0.0,
        }
        for r in holdings_rows
    ]
    if portfolio.cash_balance > 0:
        allocation_rows.append({
            "label": "Cash",
            "value": portfolio.cash_balance,
            "pct": (portfolio.cash_balance / total_value * 100) if total_value else 0.0,
        })

    sector_rows = compute_sector_allocation(position_values, portfolio.cash_balance, total_value)
    top_gainer, top_loser = compute_top_movers(holdings_rows)

    largest_position = max(holdings_rows, key=lambda r: r["value"]) if holdings_rows else None
    best_performer = max(holdings_rows, key=lambda r: r["return_pct"]) if holdings_rows else None
    worst_performer = min(holdings_rows, key=lambda r: r["return_pct"]) if holdings_rows else None
    average_return_pct = (
        sum(r["return_pct"] for r in holdings_rows) / len(holdings_rows) if holdings_rows else 0.0
    )

    stats = {
        "num_holdings": len(holdings_rows),
        "largest_position": largest_position,
        "cash_allocation_pct": (portfolio.cash_balance / total_value * 100) if total_value else 0.0,
        "average_return_pct": average_return_pct,
        "best_performer": best_performer,
        "worst_performer": worst_performer,
    }

    return {
        "portfolio_value": total_value,
        "cash_balance": portfolio.cash_balance,
        "invested_capital": invested_capital,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "total_return_pct": total_return_pct,
        "holdings": holdings_rows,
        "allocation": allocation_rows,
        "sector_allocation": sector_rows,
        "top_gainer": top_gainer,
        "top_loser": top_loser,
        "stats": stats,
        "has_transactions": len(transactions) > 0,
    }
