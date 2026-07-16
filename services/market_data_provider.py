import difflib
import json
import os
import time
from datetime import datetime, timedelta
import yfinance as yf

import requests
from dotenv import load_dotenv

from utils.exceptions import StockNotFoundError

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "company_tickers.json")
CACHE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_CONTACT_EMAIL = os.getenv("SEC_CONTACT_EMAIL", "unset-contact@example.com")

_ticker_index = None


def get_stock_price(symbol: str) -> float:
    if not FINNHUB_API_KEY:
        raise StockNotFoundError("FINNHUB_API_KEY is not set; cannot fetch a live price.")

    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": symbol, "token": FINNHUB_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise StockNotFoundError(f"Could not reach price service for {symbol}: {e}")

    if data.get("c", 0) == 0:
        raise StockNotFoundError(f"No price found for {symbol}")

    return float(data["c"])


def _load_ticker_index() -> list[tuple[str, str, str]]:
    global _ticker_index
    if _ticker_index is not None:
        return _ticker_index

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

    needs_download = not os.path.exists(CACHE_PATH)
    if os.path.exists(CACHE_PATH):
        age = time.time() - os.path.getmtime(CACHE_PATH)
        needs_download = age > CACHE_MAX_AGE_SECONDS

    if needs_download:
        try:
            response = requests.get(
                SEC_TICKERS_URL,
                headers={"User-Agent": f"PaperTrader {SEC_CONTACT_EMAIL}"},
                timeout=10,
            )
            response.raise_for_status()
            with open(CACHE_PATH, "w") as f:
                f.write(response.text)
        except Exception:
            if not os.path.exists(CACHE_PATH):
                raise StockNotFoundError(
                    "Could not download the company ticker list and no local cache is available."
                )

    with open(CACHE_PATH, "r") as f:
        raw = json.load(f)

    index = [(entry["title"].lower(), entry["ticker"], entry["title"]) for entry in raw.values()]
    _ticker_index = index
    return index


def get_stock_symbol(company_name: str) -> str:
    query = company_name.strip().lower()
    if not query:
        raise StockNotFoundError("Company name cannot be empty.")

    index = _load_ticker_index()

    for name_lower, ticker, _ in index:
        if name_lower == query:
            return ticker

    substring_matches = [item for item in index if query in item[0]]
    if substring_matches:
        substring_matches.sort(key=lambda item: len(item[0]))
        return substring_matches[0][1]

    first_words = [item[0].split()[0].rstrip(",.") for item in index]
    close = difflib.get_close_matches(query, first_words, n=1, cutoff=0.6)
    if close:
        for item, first_word in zip(index, first_words):
            if first_word == close[0]:
                return item[1]

    raise StockNotFoundError(f"No stock symbol found for '{company_name}'.")

def search_stock(query: str, limit: int = 8) -> list[dict]:
    """Returns up to `limit` {"symbol": ..., "description": ...} matches for a
    partial company name or ticker, ranked: exact match, then substring match
    (on name or ticker), then typo-tolerant fuzzy match. Used for the live
    search-as-you-type dropdown."""
    query = query.strip().lower()
    if not query:
        return []

    index = _load_ticker_index()
    seen: set[str] = set()
    results: list[dict] = []

    for name_lower, ticker, display_name in index:
        if name_lower == query and ticker not in seen:
            results.append({"symbol": ticker, "description": display_name})
            seen.add(ticker)

    scored = []
    for name_lower, ticker, display_name in index:
        if ticker in seen:
            continue
        if query in name_lower or query in ticker.lower():
            scored.append((len(name_lower), {"symbol": ticker, "description": display_name}))
            seen.add(ticker)
    scored.sort(key=lambda item: item[0])
    results.extend(item[1] for item in scored)

    if len(results) < limit:
        first_words = [item[0].split()[0].rstrip(",.") for item in index]
        close_words = set(difflib.get_close_matches(query, first_words, n=limit, cutoff=0.6))
        for item, first_word in zip(index, first_words):
            if item[1] in seen:
                continue
            if first_word in close_words:
                results.append({"symbol": item[1], "description": item[2]})
                seen.add(item[1])

    return results[:limit]


def _normalize_article(raw: dict) -> dict:
    """Converts a raw Finnhub news payload into the shape templates expect."""
    timestamp = raw.get("datetime") or 0
    try:
        published = datetime.fromtimestamp(int(timestamp)) if timestamp else None
    except (ValueError, OSError):
        published = None

    return {
        "id": raw.get("id"),
        "headline": raw.get("headline") or "Untitled",
        "summary": raw.get("summary") or "",
        "source": raw.get("source") or "Unknown source",
        "url": raw.get("url") or "",
        "image": raw.get("image") or "",
        "related": raw.get("related") or "",
        "category": raw.get("category") or "",
        "published": published,
    }


def get_market_news(category: str = "general", limit: int = 30) -> list[dict]:
    """Returns the latest general market news headlines from Finnhub."""
    if not FINNHUB_API_KEY:
        raise StockNotFoundError("FINNHUB_API_KEY is not set; cannot fetch market news.")

    url = "https://finnhub.io/api/v1/news"
    params = {"category": category, "token": FINNHUB_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise StockNotFoundError(f"Could not reach news service: {e}")

    if not isinstance(data, list):
        raise StockNotFoundError("Unexpected response from news service.")

    articles = [_normalize_article(item) for item in data]
    articles.sort(key=lambda a: a["published"] or datetime.min, reverse=True)
    return articles[:limit]


def get_company_news(symbol: str, days: int = 14, limit: int = 20) -> list[dict]:
    """Returns recent news for a specific stock symbol from Finnhub."""
    if not FINNHUB_API_KEY:
        raise StockNotFoundError("FINNHUB_API_KEY is not set; cannot fetch company news.")

    today = datetime.now().date()
    start = today - timedelta(days=days)

    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": symbol,
        "from": start.isoformat(),
        "to": today.isoformat(),
        "token": FINNHUB_API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise StockNotFoundError(f"Could not reach news service for {symbol}: {e}")

    if not isinstance(data, list):
        raise StockNotFoundError(f"Unexpected response from news service for {symbol}.")

    if not data:
        raise StockNotFoundError(f"No recent news found for {symbol}.")

    articles = [_normalize_article(item) for item in data]
    articles.sort(key=lambda a: a["published"] or datetime.min, reverse=True)
    return articles[:limit]

def get_company_profile(symbol: str) -> dict:
    """Returns Finnhub's company profile (name, industry, exchange, market
    cap, website, logo, etc.) for `symbol`. Raises StockNotFoundError if no
    API key is configured or no profile is found."""
    if not FINNHUB_API_KEY:
        raise StockNotFoundError("FINNHUB_API_KEY is not set; cannot fetch a company profile.")

    url = "https://finnhub.io/api/v1/stock/profile2"
    params = {"symbol": symbol, "token": FINNHUB_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise StockNotFoundError(f"Could not reach company profile service for {symbol}: {e}")

    if not data or not data.get("name"):
        raise StockNotFoundError(f"No company profile found for {symbol}")

    return data


def get_company_name(symbol: str) -> str | None:
    """Best-effort company display name from the cached SEC ticker index,
    used as a fallback page title when no live Finnhub profile is available."""
    try:
        index = _load_ticker_index()
    except StockNotFoundError:
        return None

    symbol = symbol.strip().upper()
    for _, ticker, display_name in index:
        if ticker == symbol:
            return display_name
    return None


HISTORY_RANGES = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "30m"),
    "1M": ("1mo", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
    "ALL": ("max", "1mo"),
}


def get_historical_prices(symbol: str, range_key: str) -> list[dict]:
    range_key = range_key.upper()

    if range_key not in HISTORY_RANGES:
        raise StockNotFoundError(f"Unsupported chart range '{range_key}'.")

    period, interval = HISTORY_RANGES[range_key]

    try:
        df = yf.Ticker(symbol).history(
            period=period,
            interval=interval,
            auto_adjust=False
        )
    except Exception as e:
        raise StockNotFoundError(f"Could not fetch chart data for {symbol}: {e}")

    if df.empty:
        raise StockNotFoundError(f"No historical data found for {symbol}.")

    points = []

    for timestamp, row in df.iterrows():
        points.append({
            "timestamp": int(timestamp.timestamp()),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]),
        })

    return points