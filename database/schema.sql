-- schema.sql
-- PaperTrader Database Schema (PostgreSQL)

-- Users: identity and credentials
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    balance NUMERIC(15,2) NOT NULL DEFAULT 100000.00,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email_verified INTEGER NOT NULL DEFAULT 0,
    verification_token TEXT
);

-- Holdings: current stock positions per user
CREATE TABLE IF NOT EXISTS holdings (
    holding_key SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    stock_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    avg_buy_price NUMERIC(15,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, stock_name)
);

-- Transactions: immutable record of every executed trade
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    stock_name TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    price NUMERIC(15,2) NOT NULL,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watchlists (
    watch_list_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS watchlist_stocks (
    watchlist_stock_id SERIAL PRIMARY KEY,
    watch_list_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    FOREIGN KEY (watch_list_id) REFERENCES watchlists(watch_list_id) ON DELETE CASCADE,
    UNIQUE (watch_list_id, stock_symbol)
);

-- Portfolio Reviews: AI-generated analyses of a user's portfolio at a point in time
CREATE TABLE IF NOT EXISTS portfolio_reviews (
    review_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    portfolio_value NUMERIC(15,2) NOT NULL,
    review_json TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Limit Orders: pending buy/sell instructions the background worker
-- monitors and executes once the market price crosses the limit price.
-- The worker (worker/worker.py) and the Flask app both read/write this
-- table -- Postgres is the single shared source of truth between them.
CREATE TABLE IF NOT EXISTS limit_orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    stock_name TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    limit_price NUMERIC(15,2) NOT NULL CHECK (limit_price > 0),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED')),
    executed_price NUMERIC(15,2),
    failure_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- The worker's main query per cycle is "which symbols have pending orders,
-- and which orders are pending for symbol X" -- this partial index keeps
-- both cheap without needing an in-memory heap (a plain indexed query is
-- enough at this scale; see worker context doc's DSA section).
CREATE INDEX IF NOT EXISTS idx_limit_orders_pending_symbol
    ON limit_orders (stock_name)
    WHERE status = 'PENDING';
