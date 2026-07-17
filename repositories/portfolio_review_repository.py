import json

from database.db_manager import DatabaseManager


class PortfolioReviewRepository:
    """Persists AI-generated portfolio reviews so a user's latest review
    survives a page refresh, and past reviews can be revisited or downloaded.
    Follows the same thin repository pattern as PortfolioRepository /
    WatchlistRepository: plain SQL in, plain dicts out, no Flask/Jinja here.
    """

    def __init__(self, db_manager: DatabaseManager | None = None):
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            self.db_manager = DatabaseManager()

    def save(self, user_id: int, portfolio_value: float, review: dict) -> int:
        cursor = self.db_manager.execute(
            "INSERT INTO portfolio_reviews (user_id, portfolio_value, review_json) VALUES (?, ?, ?)",
            (user_id, portfolio_value, json.dumps(review)),
        )
        return cursor.lastrowid

    def get_latest_by_user_id(self, user_id: int) -> dict | None:
        row = self.db_manager.fetch_one(
            """SELECT review_id, generated_at, portfolio_value, review_json
               FROM portfolio_reviews WHERE user_id = ?
               ORDER BY generated_at DESC, review_id DESC LIMIT 1""",
            (user_id,),
        )
        if row is None:
            return None
        return self._row_to_dict(row)

    def get_by_id(self, review_id: int) -> dict | None:
        row = self.db_manager.fetch_one(
            """SELECT review_id, generated_at, portfolio_value, review_json
               FROM portfolio_reviews WHERE review_id = ?""",
            (review_id,),
        )
        if row is None:
            return None
        return self._row_to_dict(row)

    def get_history_by_user_id(self, user_id: int, limit: int = 20) -> list[dict]:
        rows = self.db_manager.fetch_all(
            """SELECT review_id, generated_at, portfolio_value, review_json
               FROM portfolio_reviews WHERE user_id = ?
               ORDER BY generated_at DESC, review_id DESC LIMIT ?""",
            (user_id, limit),
        )
        return [self._row_to_dict(row) for row in rows]

    def count_since(self, user_id: int, since_iso: str) -> int:
        """Number of reviews generated for this user at/after `since_iso`
        (an ISO-ish timestamp string comparable to SQLite's CURRENT_TIMESTAMP
        format). Used to apply a simple daily generation cap."""
        row = self.db_manager.fetch_one(
            "SELECT COUNT(*) FROM portfolio_reviews WHERE user_id = ? AND generated_at >= ?",
            (user_id, since_iso),
        )
        return row[0] if row else 0

    @staticmethod
    def _row_to_dict(row) -> dict:
        review_id, generated_at, portfolio_value, review_json = row
        return {
            "review_id": review_id,
            "generated_at": generated_at,
            "portfolio_value": portfolio_value,
            "review": json.loads(review_json),
        }
