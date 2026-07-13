import os
import sqlite3


class DatabaseManager:
    def __init__(self, db_path: str, initialize_schema: bool = True):
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        if initialize_schema:
            self._initialize_schema()

    def _initialize_schema(self):
        statements = [
            "PRAGMA foreign_keys = ON;",
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                balance NUMERIC(15,2) NOT NULL DEFAULT 100000.00,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS holdings (
                holding_key INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                avg_buy_price NUMERIC(15,2) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE (user_id, stock_name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stock_name TEXT NOT NULL,
                transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
                quantity INTEGER NOT NULL,
                price NUMERIC(15,2) NOT NULL,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """,
        ]
        for statement in statements:
            try:
                self.execute(statement)
            except sqlite3.OperationalError as exc:
                if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
                    continue
                raise

    def execute(self, query: str, params: tuple | None = None):
        cursor = self._connection.cursor()
        cursor.execute(query, params or ())
        self._connection.commit()
        return cursor

    def fetch_one(self, query: str, params: tuple | None = None):
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return tuple(row) if isinstance(row, sqlite3.Row) else row

    def fetch_all(self, query: str, params: tuple | None = None):
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        if not rows:
            return []
        return [tuple(row) if isinstance(row, sqlite3.Row) else row for row in rows]

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None
