import unittest
from unittest.mock import patch

from services import market_data_provider as mdp
from utils.exceptions import StockNotFoundError


class GetStockQuoteCacheTests(unittest.TestCase):
    """get_stock_quote() is a thin TTL cache in front of _fetch_stock_quote().
    These tests patch the underlying fetch so no real network call happens,
    and drive time explicitly instead of sleeping, so the suite stays fast
    and deterministic."""

    def setUp(self):
        # Each test gets a clean cache so results don't leak between tests.
        mdp._quote_cache.clear()

    def test_second_call_within_ttl_hits_cache(self):
        fake_quote = {"c": 150.0}
        with patch.object(mdp, "_fetch_stock_quote", return_value=fake_quote) as mock_fetch, \
             patch.object(mdp.time, "time", side_effect=[100.0, 105.0]):
            first = mdp.get_stock_quote("AAPL")
            second = mdp.get_stock_quote("AAPL")

        self.assertEqual(first, fake_quote)
        self.assertEqual(second, fake_quote)
        mock_fetch.assert_called_once_with("AAPL")

    def test_call_after_ttl_expires_refetches(self):
        first_quote = {"c": 150.0}
        second_quote = {"c": 151.5}
        with patch.object(mdp, "_fetch_stock_quote", side_effect=[first_quote, second_quote]) as mock_fetch, \
             patch.object(mdp.time, "time", side_effect=[100.0, 111.0]):
            first = mdp.get_stock_quote("AAPL")
            second = mdp.get_stock_quote("AAPL")

        self.assertEqual(first, first_quote)
        self.assertEqual(second, second_quote)
        self.assertEqual(mock_fetch.call_count, 2)

    def test_symbol_is_normalized_before_caching(self):
        fake_quote = {"c": 150.0}
        with patch.object(mdp, "_fetch_stock_quote", return_value=fake_quote) as mock_fetch, \
             patch.object(mdp.time, "time", side_effect=[100.0, 100.0]):
            mdp.get_stock_quote("  aapl ")
            mdp.get_stock_quote("AAPL")

        mock_fetch.assert_called_once_with("AAPL")

    def test_failed_lookup_is_not_cached(self):
        with patch.object(
            mdp, "_fetch_stock_quote", side_effect=StockNotFoundError("no price")
        ) as mock_fetch, patch.object(mdp.time, "time", side_effect=[100.0, 100.0]):
            with self.assertRaises(StockNotFoundError):
                mdp.get_stock_quote("AAPL")
            with self.assertRaises(StockNotFoundError):
                mdp.get_stock_quote("AAPL")

        self.assertEqual(mock_fetch.call_count, 2)

    def test_get_stock_price_reads_close_price_from_quote(self):
        with patch.object(mdp, "get_stock_quote", return_value={"c": 172.34}):
            price = mdp.get_stock_price("AAPL")

        self.assertEqual(price, 172.34)


if __name__ == "__main__":
    unittest.main()
