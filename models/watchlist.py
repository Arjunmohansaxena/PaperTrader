class WatchList:

    def __init__(self, watch_list_id: int | None, user_id: int, name: str, stocks: list = None):
        self.watch_list_id = watch_list_id
        self.user_id = user_id
        self.name = name
        self.stocks = stocks if stocks is not None else []

    def add_stock(self, stock_symbol: str):
        if not self.contains_stock(stock_symbol):
            self.stocks.append(stock_symbol)
    
    def remove_stock(self, stock_symbol: str):
        if self.contains_stock(stock_symbol):
            self.stocks.remove(stock_symbol)    
        
    def contains_stock(self, stock_symbol: str) -> bool:
        return stock_symbol in self.stocks

    def get_all_stocks(self) -> list:
        return self.stocks
    
    def display_watchlist(self):
        print(f"Watchlist: {self.name}")
        for stock in self.stocks:
            print(f"- {stock}")