import sqlite3


class DatabaseManager:
    def __init__(self, db_path:str):
        self.db_path = db_path
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row

    def execute(self, query: str, params: tuple | None = None):
        cursor = self._connection.cursor()
        cursor.execute(query, params or ())
        self._connection.commit()
        return cursor

    def fetch_one(self, query: str, params: tuple | None = None):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetch_all(self, query: str, params: tuple | None = None):
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def close(self):
        self._connection.close()
