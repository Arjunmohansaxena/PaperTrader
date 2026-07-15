import os
import tempfile
import unittest
 
from database.db_manager import DatabaseManager
 
 
class DatabaseManagerTests(unittest.TestCase):
    def test_execute_fetch_methods(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "papertrader.db")
            with DatabaseManager(db_path) as manager:
                manager.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
                manager.execute("INSERT INTO users (name) VALUES (?)", ("alice",))
 
                row = manager.fetch_one("SELECT name FROM users WHERE id = ?", (1,))
                rows = manager.fetch_all("SELECT name FROM users ORDER BY id")
 
                self.assertEqual(row[0], "alice")
                self.assertEqual(rows, [("alice",)])
 
 
if __name__ == "__main__":
    unittest.main()
 