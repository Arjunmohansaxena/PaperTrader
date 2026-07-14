-- schema.sql
-- PaperTrader Database Schema (SQLite)

PRAGMA foreign_keys = ON;

-- Users: identity and credentials
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    balance NUMERIC(15,2) NOT NULL DEFAULT 100000.00,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Holdings: current stock positions per user
CREATE TABLE IF NOT EXISTS holdings (
    holding_key INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    avg_buy_price NUMERIC(15,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, stock_name)
);

-- Transactions: immutable record of every executed trade
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_name TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    price NUMERIC(15,2) NOT NULL,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watchlists (
    watch_list_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS watchlist_stocks (
    watchlist_stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_list_id INTEGER NOT NULL,
    stock_symbol TEXT NOT NULL,
    FOREIGN KEY (watch_list_id) REFERENCES watchlists(watch_list_id) ON DELETE CASCADE,
    UNIQUE (watch_list_id, stock_symbol)
);