import os
import tempfile
import unittest
 
from database.db_manager import DatabaseManager
from repositories.watchlist_repository import WatchlistRepository
 
 
class WatchlistRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "papertrader.db")
        self.db_manager = DatabaseManager(db_path)
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
        with open(schema_path) as schema_file:
            self.db_manager.executescript(schema_file.read())
        self.db_manager.execute(
            "INSERT INTO users (user_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (1, "alice", "alice@example.com", "hash"),
        )
        self.repository = WatchlistRepository(self.db_manager)
 
    def tearDown(self):
        self.db_manager.close()
        self.temp_dir.cleanup()
 
    def test_create_watchlist_assigns_an_id(self):
        watchlist = self.repository.create_watchlist(user_id=1, name="Tech")
        self.assertIsNotNone(watchlist.watch_list_id)
        self.assertEqual(watchlist.name, "Tech")
        self.assertEqual(watchlist.stocks, [])
 
    def test_add_and_get_stocks(self):
        watchlist = self.repository.create_watchlist(user_id=1, name="Tech")
        self.repository.add_stock(watchlist.watch_list_id, "aapl")
        self.repository.add_stock(watchlist.watch_list_id, "TSLA")
 
        reloaded = self.repository.get_by_id(watchlist.watch_list_id)
        self.assertEqual(reloaded.stocks, ["AAPL", "TSLA"])
 
    def test_add_stock_does_not_duplicate_in_the_database(self):
        watchlist = self.repository.create_watchlist(user_id=1, name="Tech")
        self.repository.add_stock(watchlist.watch_list_id, "AAPL")
        self.repository.add_stock(watchlist.watch_list_id, "AAPL")
 
        reloaded = self.repository.get_by_id(watchlist.watch_list_id)
        self.assertEqual(reloaded.stocks, ["AAPL"])
 
    def test_remove_stock(self):
        watchlist = self.repository.create_watchlist(user_id=1, name="Tech")
        self.repository.add_stock(watchlist.watch_list_id, "AAPL")
        self.repository.add_stock(watchlist.watch_list_id, "TSLA")
        self.repository.remove_stock(watchlist.watch_list_id, "AAPL")
 
        reloaded = self.repository.get_by_id(watchlist.watch_list_id)
        self.assertEqual(reloaded.stocks, ["TSLA"])
 
    def test_get_by_user_id_returns_all_watchlists_for_that_user(self):
        self.repository.create_watchlist(user_id=1, name="Tech")
        self.repository.create_watchlist(user_id=1, name="Dividends")
 
        watchlists = self.repository.get_by_user_id(1)
        names = sorted(wl.name for wl in watchlists)
        self.assertEqual(names, ["Dividends", "Tech"])
 
    def test_delete_removes_watchlist_and_its_stocks(self):
        watchlist = self.repository.create_watchlist(user_id=1, name="Tech")
        self.repository.add_stock(watchlist.watch_list_id, "AAPL")
 
        self.repository.delete(watchlist.watch_list_id)
 
        self.assertIsNone(self.repository.get_by_id(watchlist.watch_list_id))
 
    def test_get_by_id_returns_none_when_missing(self):
        self.assertIsNone(self.repository.get_by_id(9999))
 
 
if __name__ == "__main__":
    unittest.main()