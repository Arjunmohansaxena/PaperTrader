import unittest
 
from models.watchlist import WatchList
 
 
class WatchListTests(unittest.TestCase):
    def test_add_stock_appends_new_symbol(self):
        watchlist = WatchList(watch_list_id=1, user_id=1, name="Tech")
        watchlist.add_stock("AAPL")
        self.assertEqual(watchlist.get_all_stocks(), ["AAPL"])
 
    def test_add_stock_does_not_duplicate(self):
        watchlist = WatchList(watch_list_id=1, user_id=1, name="Tech")
        watchlist.add_stock("AAPL")
        watchlist.add_stock("AAPL")
        self.assertEqual(watchlist.get_all_stocks(), ["AAPL"])
 
    def test_remove_stock(self):
        watchlist = WatchList(watch_list_id=1, user_id=1, name="Tech", stocks=["AAPL", "TSLA"])
        watchlist.remove_stock("AAPL")
        self.assertEqual(watchlist.get_all_stocks(), ["TSLA"])
 
    def test_remove_stock_not_present_is_a_no_op(self):
        watchlist = WatchList(watch_list_id=1, user_id=1, name="Tech", stocks=["AAPL"])
        watchlist.remove_stock("TSLA")
        self.assertEqual(watchlist.get_all_stocks(), ["AAPL"])
 
    def test_contains_stock(self):
        watchlist = WatchList(watch_list_id=1, user_id=1, name="Tech", stocks=["AAPL"])
        self.assertTrue(watchlist.contains_stock("AAPL"))
        self.assertFalse(watchlist.contains_stock("TSLA"))
 
    def test_stocks_defaults_to_empty_list(self):
        watchlist = WatchList(watch_list_id=None, user_id=1, name="Empty")
        self.assertEqual(watchlist.get_all_stocks(), [])
 
 
if __name__ == "__main__":
    unittest.main()
 