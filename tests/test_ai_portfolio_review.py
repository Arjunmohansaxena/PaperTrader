import os
import tempfile
import unittest

from database.db_manager import DatabaseManager
from repositories.portfolio_review_repository import PortfolioReviewRepository
from services.ai_review_service import (
    _extract_json_text,
    _format_metrics_for_prompt,
    generate_portfolio_review,
)
from utils.exceptions import AIReviewError

SAMPLE_METRICS = {
    "portfolio_value": 105230.50,
    "cash_balance": 5230.50,
    "invested_capital": 95000.0,
    "unrealized_pnl": 5230.5,
    "realized_pnl": 1200.0,
    "total_return_pct": 5.23,
    "holdings": [
        {"symbol": "AAPL", "name": "Apple Inc", "quantity": 50, "value": 10000.0, "return_pct": 12.3},
        {"symbol": "TSLA", "name": "Tesla Inc", "quantity": 20, "value": 85000.0, "return_pct": 2.1},
    ],
    "sector_allocation": [
        {"sector": "Technology", "pct": 90.3},
        {"sector": "Cash", "pct": 9.7},
    ],
    "stats": {
        "num_holdings": 2,
        "cash_allocation_pct": 4.97,
        "largest_position": {"name": "Tesla Inc", "value": 85000.0},
        "best_performer": {"name": "Apple Inc", "return_pct": 12.3},
        "worst_performer": {"name": "Tesla Inc", "return_pct": 2.1},
    },
    "has_transactions": True,
}

VALID_JSON_RESPONSE = (
    '{"summary": "Concentrated in tech.", '
    '"risk_flags": ["Single stock is 80% of holdings"], '
    '"diversification_notes": "Low diversification.", '
    '"strengths": ["Positive overall return"], '
    '"suggestions": ["Spread capital across more sectors"]}'
)


class PromptFormattingTests(unittest.TestCase):
    def test_format_includes_key_figures(self):
        prompt = _format_metrics_for_prompt(SAMPLE_METRICS)
        self.assertIn("105,230.50", prompt)
        self.assertIn("AAPL", prompt)
        self.assertIn("Technology: 90.3%", prompt)

    def test_format_handles_empty_holdings(self):
        empty_metrics = dict(SAMPLE_METRICS)
        empty_metrics["holdings"] = []
        empty_metrics["stats"] = {
            "num_holdings": 0,
            "cash_allocation_pct": 100.0,
            "largest_position": None,
            "best_performer": None,
            "worst_performer": None,
        }
        prompt = _format_metrics_for_prompt(empty_metrics)
        self.assertIn("Holdings: none", prompt)


class ResponseParsingTests(unittest.TestCase):
    def test_parses_plain_json(self):
        result = _extract_json_text(VALID_JSON_RESPONSE)
        self.assertEqual(result["summary"], "Concentrated in tech.")
        self.assertIn("risk_flags", result)

    def test_strips_markdown_fences(self):
        fenced = "```json\n" + VALID_JSON_RESPONSE + "\n```"
        result = _extract_json_text(fenced)
        self.assertEqual(result["diversification_notes"], "Low diversification.")

    def test_raises_on_invalid_json(self):
        with self.assertRaises(AIReviewError):
            _extract_json_text("not json at all")

    def test_raises_on_missing_required_field(self):
        with self.assertRaises(AIReviewError):
            _extract_json_text('{"summary": "ok"}')


class GenerateReviewGuardTests(unittest.TestCase):
    def test_raises_without_api_key(self):
        import services.ai_review_service as svc

        original_key = svc.GEMINI_API_KEY
        svc.GEMINI_API_KEY = None
        try:
            with self.assertRaises(AIReviewError):
                generate_portfolio_review(SAMPLE_METRICS)
        finally:
            svc.GEMINI_API_KEY = original_key

    def test_raises_on_empty_portfolio(self):
        import services.ai_review_service as svc

        original_key = svc.GEMINI_API_KEY
        svc.GEMINI_API_KEY = "fake-key-for-test"
        try:
            with self.assertRaises(AIReviewError):
                generate_portfolio_review({"holdings": [], "cash_balance": 0})
        finally:
            svc.GEMINI_API_KEY = original_key


class PortfolioReviewRepositoryTests(unittest.TestCase):
    def test_save_and_retrieve_latest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "papertrader.db")
            schema_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql"
            )

            with DatabaseManager(db_path) as db_manager:
                with open(schema_path) as schema_file:
                    db_manager.executescript(schema_file.read())

                db_manager.execute(
                    "INSERT INTO users (user_id, username, email, password_hash, balance) "
                    "VALUES (1, 'tester', 'tester@example.com', 'hash', 100000.0)"
                )

                repo = PortfolioReviewRepository(db_manager)
                review = {
                    "summary": "Test summary",
                    "risk_flags": [],
                    "diversification_notes": "",
                    "strengths": [],
                    "suggestions": [],
                }

                self.assertIsNone(repo.get_latest_by_user_id(1))

                review_id = repo.save(1, 100000.0, review)
                latest = repo.get_latest_by_user_id(1)

                self.assertEqual(latest["review_id"], review_id)
                self.assertEqual(latest["review"]["summary"], "Test summary")
                self.assertEqual(latest["portfolio_value"], 100000.0)

    def test_history_returns_most_recent_first(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "papertrader.db")
            schema_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql"
            )

            with DatabaseManager(db_path) as db_manager:
                with open(schema_path) as schema_file:
                    db_manager.executescript(schema_file.read())

                db_manager.execute(
                    "INSERT INTO users (user_id, username, email, password_hash, balance) "
                    "VALUES (1, 'tester', 'tester@example.com', 'hash', 100000.0)"
                )

                repo = PortfolioReviewRepository(db_manager)
                first_id = repo.save(1, 100000.0, {"summary": "first", "risk_flags": [],
                                                     "diversification_notes": "", "strengths": [],
                                                     "suggestions": []})
                second_id = repo.save(1, 101000.0, {"summary": "second", "risk_flags": [],
                                                      "diversification_notes": "", "strengths": [],
                                                      "suggestions": []})

                history = repo.get_history_by_user_id(1)
                self.assertEqual(history[0]["review_id"], second_id)
                self.assertEqual(history[1]["review_id"], first_id)


if __name__ == "__main__":
    unittest.main()
