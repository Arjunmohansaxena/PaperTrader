import os

import psycopg2
import psycopg2.extensions

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/papertrader"


class DatabaseManager:
    """Thin wrapper around a PostgreSQL connection.

    Render's free-tier web services have an ephemeral filesystem: anything
    written inside the container (like a SQLite .db file) is wiped on every
    redeploy or restart. Render's free PostgreSQL instance is a separate,
    persistent service, so data survives redeploys. This class replaces the
    old sqlite3-backed version with psycopg2, while keeping the same public
    interface (execute/fetch_one/fetch_all/executescript/ensure_column) so
    the repository classes barely need to change.

    Connects using the DATABASE_URL environment variable that Render (and
    most Postgres hosts) inject automatically when a Postgres instance is
    attached to a service. Falls back to a local default for local dev.
    """

    def __init__(self, database_url: str | None = None):
        database_url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
        self._connection = psycopg2.connect(database_url)
        self._connection.autocommit = False
        self._use_float_for_numeric()

    def _use_float_for_numeric(self):
        
        dec2float = psycopg2.extensions.new_type(
            psycopg2.extensions.DECIMAL.values,
            "DEC2FLOAT",
            lambda value, curs: float(value) if value is not None else None,
        )
        psycopg2.extensions.register_type(dec2float, self._connection)

    @staticmethod
    def _to_pg_placeholders(query: str) -> str:
        # Repositories were written against SQLite's "?" placeholder style.
        # psycopg2/Postgres uses "%s". None of our queries contain a literal
        # "?" inside a string value, so a straight substitution is safe and
        # avoids rewriting every query string across the repositories.
        return query.replace("?", "%s")

    def execute(self, query: str, params: tuple | None = None):
        cursor = self._connection.cursor()
        cursor.execute(self._to_pg_placeholders(query), params or ())
        self._connection.commit()
        return cursor

    def fetch_one(self, query: str, params: tuple | None = None):
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return tuple(row) if row is not None else None

    def fetch_all(self, query: str, params: tuple | None = None):
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [tuple(row) for row in rows]

    def executescript(self, script: str):
        # Unlike sqlite3, psycopg2's execute() can run a multi-statement
        # SQL string (e.g. a full schema.sql) in one call.
        cursor = self._connection.cursor()
        cursor.execute(script)
        self._connection.commit()

    def ensure_column(self, table: str, column: str, ddl: str):
        """Add a column to an existing table if it's not already there.

        Postgres supports ADD COLUMN IF NOT EXISTS natively, so this is
        simpler than the old SQLite version that had to catch a
        "duplicate column" error.
        """
        cursor = self._connection.cursor()
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}")
        self._connection.commit()

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()