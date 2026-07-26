import unittest

from database.db_manager import DatabaseManager
from tests.db_test_utils import drop_test_database, make_test_database_url


class DatabaseManagerTests(unittest.TestCase):
    def test_execute_fetch_methods(self):
        db_url = make_test_database_url()
        try:
            with DatabaseManager(db_url) as manager:
                manager.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT)")
                manager.execute("INSERT INTO users (name) VALUES (?)", ("alice",))

                row = manager.fetch_one("SELECT name FROM users WHERE id = ?", (1,))
                rows = manager.fetch_all("SELECT name FROM users ORDER BY id")

                self.assertEqual(row[0], "alice")
                self.assertEqual(rows, [("alice",)])
        finally:
            drop_test_database(db_url)


if __name__ == "__main__":
    unittest.main()
