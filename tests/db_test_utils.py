import os
import uuid

import psycopg2

# Admin connection used only to CREATE/DROP throwaway test databases.
# Points at the default "postgres" maintenance database, not the app's
# own database. Override via TEST_DATABASE_ADMIN_URL if your local/CI
# Postgres uses different credentials.
TEST_DATABASE_ADMIN_URL = os.environ.get(
    "TEST_DATABASE_ADMIN_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)


def make_test_database_url() -> str:
    """Create a fresh, uniquely-named Postgres database and return its URL.

    This is the Postgres equivalent of the old "tempfile.TemporaryDirectory()
    + SQLite path" pattern: each test gets its own throwaway database so
    tests can't see each other's data, and it's dropped in tearDown.
    """
    db_name = f"papertrader_test_{uuid.uuid4().hex[:12]}"
    admin_conn = psycopg2.connect(TEST_DATABASE_ADMIN_URL)
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        admin_conn.close()

    base_url = TEST_DATABASE_ADMIN_URL.rsplit("/", 1)[0]
    return f"{base_url}/{db_name}"


def drop_test_database(database_url: str) -> None:
    """Drop a database created by make_test_database_url."""
    db_name = database_url.rsplit("/", 1)[-1]
    admin_conn = psycopg2.connect(TEST_DATABASE_ADMIN_URL)
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
    finally:
        admin_conn.close()
