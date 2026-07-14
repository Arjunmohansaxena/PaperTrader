from database.db_manager import DatabaseManager
from models.watchlist import WatchList

class WatchlistRepository:
    def __init__(self, db_manager: DatabaseManager | None = None):
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            self.db_manager = DatabaseManager()

    def create_watchlist(self, user_id: int, name: str) -> WatchList:
        cursor = self.db_manager.execute(
            "INSERT INTO watchlists (user_id, name) VALUES (?, ?)",
            (user_id, name),
        )
        return WatchList(watch_list_id=cursor.lastrowid, user_id=user_id, name=name)

    def get_by_id(self, watch_list_id: int) -> WatchList | None:
        row = self.db_manager.fetch_one(
            "SELECT watch_list_id, user_id, name FROM watchlists WHERE watch_list_id = ?",
            (watch_list_id,),
        )
        if row is None:
            return None
        stocks = self._get_stocks(watch_list_id)
        return WatchList(watch_list_id=row[0], user_id=row[1], name=row[2], stocks=stocks)

    def get_by_user_id(self, user_id: int) -> list[WatchList]:
        rows = self.db_manager.fetch_all(
            "SELECT watch_list_id, user_id, name FROM watchlists WHERE user_id = ?",
            (user_id,),
        )
        watchlists = []
        for row in rows:
            stocks = self._get_stocks(row[0])
            watchlists.append(WatchList(watch_list_id=row[0], user_id=row[1], name=row[2], stocks=stocks))
        return watchlists

    def add_stock(self, watch_list_id: int, stock_symbol: str) -> None:
        symbol = stock_symbol.strip().upper()
        if not symbol:
            return
        self.db_manager.execute(
            "INSERT OR IGNORE INTO watchlist_stocks (watch_list_id, stock_symbol) VALUES (?, ?)",
            (watch_list_id, symbol),
        )

    def remove_stock(self, watch_list_id: int, stock_symbol: str) -> None:
        symbol = stock_symbol.strip().upper()
        self.db_manager.execute(
            "DELETE FROM watchlist_stocks WHERE watch_list_id = ? AND stock_symbol = ?",
            (watch_list_id, symbol),
        )

    def delete(self, watch_list_id: int) -> None:
        self.db_manager.execute(
            "DELETE FROM watchlist_stocks WHERE watch_list_id = ?",
            (watch_list_id,),
        )
        self.db_manager.execute(
            "DELETE FROM watchlists WHERE watch_list_id = ?",
            (watch_list_id,),
        )

    def _get_stocks(self, watch_list_id: int) -> list[str]:
        rows = self.db_manager.fetch_all(
            "SELECT stock_symbol FROM watchlist_stocks WHERE watch_list_id = ? ORDER BY stock_symbol",
            (watch_list_id,),
        )
        return [row[0] for row in rows]