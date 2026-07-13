import os
import sqlite3


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row

    def executescript(self, script: str):
        self._connection.executescript(script)
        self._connection.commit()

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()