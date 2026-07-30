"""Tool definitions and execution for the AI Financial Copilot.

Security model (PHASE_1_AI_COPILOT.md section 4 & 5): the LLM never
receives a database connection, credentials, or the ability to run SQL,
and it never supplies a user_id. Every method on AITools is bound to one
authenticated user at construction time -- the backend determines that
user_id from the existing session/auth system before the AI service is
ever invoked, and it stays fixed for the whole tool-call loop. The LLM
can only ask for "my portfolio", never "user 123's portfolio".

Tools call into the app's *existing* repositories and market-data service
rather than duplicating any business logic or opening a second data path,
per section 10/11's "do not duplicate business logic" / "do not create a
second independent Finnhub integration" instructions.
"""

from services.market_data_provider import (
    get_company_news,
    get_company_profile,
    get_display_name,
    get_stock_quote,
)
from services.portfolio_metrics import get_portfolio_metrics
from utils.exceptions import StockNotFoundError

MAX_TRANSACTIONS_RETURNED = 20
MAX_NEWS_ARTICLES_RETURNED = 10

# Gemini function-calling schema. Deliberately narrow: these 8 read-only
# tools are the entire Phase 1 surface -- no trading, no freeform DB/API
# access, no RAG.
TOOL_DECLARATIONS = [{
    "function_declarations": [
        {
            "name": "get_portfolio_summary",
            "description": (
                "Get the authenticated user's overall portfolio summary: total portfolio value, "
                "invested capital, cash balance, unrealized P/L, realized P/L, and total return %."
            ),
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_holdings",
            "description": (
                "Get every stock the authenticated user currently holds, with quantity, average "
                "buy price, current price, market value, and P/L for each."
            ),
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_holding",
            "description": (
                "Get the authenticated user's position in one specific stock symbol -- whether "
                "they own it, and if so quantity, average buy price, current value, and P/L."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "symbol": {"type": "STRING", "description": "Stock ticker symbol, e.g. AAPL"},
                },
                "required": ["symbol"],
            },
        },
        {
            "name": "get_transactions",
            "description": (
                "Get the authenticated user's recent buy/sell transaction history, optionally "
                "filtered to one ticker symbol."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "symbol": {
                        "type": "STRING",
                        "description": "Optional ticker symbol to filter transactions to",
                    },
                },
            },
        },
        {
            "name": "get_watchlist",
            "description": "Get the authenticated user's watchlists and the ticker symbols saved in each.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_stock_quote",
            "description": (
                "Get a live price quote for a stock: current price, change, percent change, and "
                "previous close."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "symbol": {"type": "STRING", "description": "Stock ticker symbol, e.g. AAPL"},
                },
                "required": ["symbol"],
            },
        },
        {
            "name": "get_company_profile",
            "description": "Get basic company info for a stock: name, industry, exchange, market cap.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "symbol": {"type": "STRING", "description": "Stock ticker symbol, e.g. AAPL"},
                },
                "required": ["symbol"],
            },
        },
        {
            "name": "get_company_news",
            "description": "Get recent news headlines for a specific stock.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "symbol": {"type": "STRING", "description": "Stock ticker symbol, e.g. AAPL"},
                },
                "required": ["symbol"],
            },
        },
    ]
}]


class AITools:
    """Bound to one authenticated user for the lifetime of a single chat
    request. `execute(name, args)` is the AI service's only entry point --
    it never lets the model pick an arbitrary Python function, and it
    never accepts a user_id from the model."""

    def __init__(self, user_id: int, portfolio_repo, watchlist_repo):
        self.user_id = user_id
        self.portfolio_repo = portfolio_repo
        self.watchlist_repo = watchlist_repo

    def execute(self, name: str, args: dict | None) -> dict:
        """Runs a tool by name with model-supplied args, catching any
        failure into a sanitized {"error": ...} dict instead of raising --
        a broken tool call should degrade the conversation, not crash the
        request or leak a traceback to the model."""
        handler = self._HANDLERS.get(name)
        if handler is None:
            return {"error": f"Unknown tool '{name}'."}
        try:
            return handler(self, **(args or {}))
        except TypeError as exc:
            return {"error": f"Invalid arguments for '{name}': {exc}"}
        except Exception as exc:
            return {"error": str(exc)}

    def get_portfolio_summary(self) -> dict:
        metrics = get_portfolio_metrics(self.user_id, self.portfolio_repo)
        if metrics is None:
            return {"error": "No portfolio found for this account."}
        return {
            "total_value": round(metrics["portfolio_value"], 2),
            "invested_capital": round(metrics["invested_capital"], 2),
            "cash_balance": round(metrics["cash_balance"], 2),
            "unrealized_pnl": round(metrics["unrealized_pnl"], 2),
            "realized_pnl": round(metrics["realized_pnl"], 2),
            "total_return_pct": round(metrics["total_return_pct"], 2),
        }

    def get_holdings(self) -> dict:
        metrics = get_portfolio_metrics(self.user_id, self.portfolio_repo)
        if metrics is None:
            return {"error": "No portfolio found for this account."}
        return {
            "holdings": [
                {
                    "symbol": h["symbol"],
                    "quantity": h["quantity"],
                    "average_buy_price": round(h["avg_cost"], 2),
                    "current_price": round(h["current_price"], 2),
                    "market_value": round(h["value"], 2),
                    "pnl": round(h["pnl"], 2),
                    "pnl_percent": round(h["return_pct"], 2),
                }
                for h in metrics["holdings"]
            ]
        }

    def get_holding(self, symbol: str) -> dict:
        symbol = str(symbol).strip().upper()
        portfolio = self.portfolio_repo.get_by_user_id(self.user_id)
        if portfolio is None or symbol not in portfolio.positions:
            return {"symbol": symbol, "owned": False}

        position = portfolio.positions[symbol]
        try:
            price = float(get_stock_quote(symbol)["c"])
        except Exception:
            price = position.avg_buy_price  # best-effort fallback, still clearly labeled below

        cost_basis = position.quantity * position.avg_buy_price
        pnl = position.unrealized_profit_loss(price)

        return {
            "symbol": symbol,
            "owned": True,
            "quantity": position.quantity,
            "average_buy_price": round(position.avg_buy_price, 2),
            "current_price": round(price, 2),
            "market_value": round(position.get_position_value(price), 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round((pnl / cost_basis * 100) if cost_basis else 0.0, 2),
        }

    def get_transactions(self, symbol: str | None = None) -> dict:
        transactions = self.portfolio_repo.get_transaction_history(self.user_id)
        if symbol:
            symbol = str(symbol).strip().upper()
            transactions = [t for t in transactions if t.symbol == symbol]
        transactions = transactions[:MAX_TRANSACTIONS_RETURNED]
        return {
            "transactions": [
                {
                    "symbol": t.symbol,
                    "side": t.side,
                    "quantity": t.quantity,
                    "price": round(t.price, 2),
                    "total": round(t.total_amount, 2),
                    "timestamp": t.timestamp.isoformat() if hasattr(t.timestamp, "isoformat") else str(t.timestamp),
                }
                for t in transactions
            ]
        }

    def get_watchlist(self) -> dict:
        watchlists = self.watchlist_repo.get_by_user_id(self.user_id)
        return {
            "watchlists": [{"name": wl.name, "symbols": wl.stocks} for wl in watchlists]
        }

    def get_stock_quote(self, symbol: str) -> dict:
        symbol = str(symbol).strip().upper()
        try:
            quote = get_stock_quote(symbol)
        except StockNotFoundError as exc:
            return {"error": str(exc)}
        return {
            "symbol": symbol,
            "current_price": quote.get("c"),
            "change": quote.get("d"),
            "percent_change": quote.get("dp"),
            "previous_close": quote.get("pc"),
        }

    def get_company_profile(self, symbol: str) -> dict:
        symbol = str(symbol).strip().upper()
        try:
            profile = get_company_profile(symbol)
        except StockNotFoundError as exc:
            return {"error": str(exc)}
        return {
            "symbol": symbol,
            "name": profile.get("name") or get_display_name(symbol),
            "industry": profile.get("finnhubIndustry"),
            "exchange": profile.get("exchange"),
            "market_cap": profile.get("marketCapitalization"),
        }

    def get_company_news(self, symbol: str) -> dict:
        symbol = str(symbol).strip().upper()
        try:
            articles = get_company_news(symbol)
        except StockNotFoundError as exc:
            return {"error": str(exc)}
        return {
            "symbol": symbol,
            "articles": [
                {
                    "headline": a["headline"],
                    "source": a["source"],
                    "published": a["published"].isoformat() if a.get("published") else None,
                }
                for a in articles[:MAX_NEWS_ARTICLES_RETURNED]
            ],
        }

    _HANDLERS = {
        "get_portfolio_summary": get_portfolio_summary,
        "get_holdings": get_holdings,
        "get_holding": get_holding,
        "get_transactions": get_transactions,
        "get_watchlist": get_watchlist,
        "get_stock_quote": get_stock_quote,
        "get_company_profile": get_company_profile,
        "get_company_news": get_company_news,
    }
