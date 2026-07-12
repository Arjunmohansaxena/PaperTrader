import yfinance as yf

def get_stock_price(symbol: str) -> float:
    try:
        stock = yf.Ticker(symbol)
        price = stock.history(period="1d")["Close"].iloc[-1]
        return price
    except Exception as e:
        raise ValueError(f"Could not fetch stock price for {symbol}: {e}")

