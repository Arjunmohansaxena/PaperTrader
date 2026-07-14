# PaperTrader

A simple command-line paper trading app. Register a user, get a starting cash
balance, and buy/sell stocks against live or manually-entered prices — all
backed by a local SQLite database.

## Features

- User registration and login (passwords are hashed, never stored in plain text)
- Buy and sell stocks against a virtual cash balance
- Live price lookups via [yfinance](https://pypi.org/project/yfinance/), with
  manual price entry as a fallback if a live price can't be fetched
- Persistent portfolio and transaction history (SQLite)
- Unit tests covering the data models and repository layer

## Requirements

- Python 3.11+
- (Optional) `yfinance`, for live stock prices — see [Installation](#installation)

## Installation

```bash
git clone https://github.com/Arjunmohansaxena/PaperTrader.git
cd PaperTrader
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

`yfinance` is optional. If it's not installed (or a live lookup fails), the
app will prompt you to enter a stock price manually instead of crashing.

## Running the app

```bash
python main.py
```

You'll be dropped into a menu:

```
=== PaperTrader ===
1) Log in
2) Register
3) Quit
```

Register a new account to get a starting cash balance of $100,000, then log
in to reach the trading menu:

```
=== <username>'s Portfolio ===
1) View portfolio
2) Buy stock
3) Sell stock
4) Transaction history
5) Log out
```

The database file is created automatically at `database/PaperTrader.db` on
first run — no manual setup required.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

## Project structure

```
PaperTrader/
├── main.py                          # CLI entry point
├── database/
│   ├── db_manager.py                 # Thin SQLite wrapper (execute/fetch/executescript)
│   └── schema.sql                    # Table definitions (users, holdings, transactions)
├── models/
│   ├── user.py                       # User + password hashing/verification
│   ├── portfolio.py                  # Cash balance + open positions, buy/sell logic
│   ├── position.py                   # A single held stock position
│   └── transaction.py                # A single buy/sell record
├── repositories/
│   ├── user_repository.py            # User persistence (create, authenticate, look up)
│   └── portfolio_repository.py       # Portfolio + transaction persistence
├── services/
│   └── market_data_provider.py       # Live price lookups via yfinance
├── utils/
│   └── exceptions.py                 # Custom exception types (not yet wired into the app)
├── tests/                            # Unit tests
└── docs/                             # ER diagram, design notes
```

## Database schema

Three tables: `users`, `holdings`, and `transactions`. See
`docs/PaperTrader_ER_diagram.png` for the full entity-relationship diagram.

- `users` — one row per account; holds cash `balance`
- `holdings` — one row per stock a user currently owns (`stock_name`, `quantity`, `avg_buy_price`)
- `transactions` — a full log of every buy/sell, independent of current holdings

## Known limitations / roadmap

- `utils/exceptions.py` defines custom exceptions (e.g. `InsufficientFundsError`)
  that aren't wired into the app yet — errors currently surface as plain `ValueError`.
- No password strength requirements or email validation on registration yet.
- Live prices depend on Yahoo Finance's public data via `yfinance`, which can
  occasionally return no data for a valid ticker; manual entry is the fallback.
- Single-user CLI only — no web UI yet.

## License

Add a license of your choice (e.g. MIT) if you plan to make this repository public.
