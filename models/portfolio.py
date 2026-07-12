from models.position import Position


class Portfolio:
    def __init__(self,cash_balance:float,positions:dict=None):
        self.cash_balance = cash_balance
        self.positions = positions if positions is not None else {}

    def buy_stock(self,symbol:str,quantity:int,price:float):
        total_cost = quantity * price
        if total_cost > self.cash_balance:
            raise ValueError("Insufficient cash balance to buy stock.")
        if symbol in self.positions:
            self.positions[symbol].add_share(quantity, price)
        else:
            self.positions[symbol] = Position(symbol, quantity, price)
        self.cash_balance -= total_cost
    
    def sell_stock(self,symbol:str,quantity:int,price:float):
        if symbol not in self.positions:
            raise ValueError("No shares of this stock to sell.")
        position = self.positions[symbol]
        if quantity > position.quantity:
            raise ValueError("Cannot sell more shares than currently held.")
        position.remove_share(quantity)
        self.cash_balance += quantity * price
        if position.quantity == 0:
            del self.positions[symbol]
        
    def get_portfolio_value(self,current_prices:dict):
        total_value = self.cash_balance
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_value += position.get_position_value(current_prices[symbol])
            else:
                raise ValueError(f"Current price for {symbol} not provided.")
        return total_value

    def total_holdings_value(self,current_prices:dict):
        total_value = 0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_value += position.get_position_value(current_prices[symbol])
            else:
                raise ValueError(f"Current price for {symbol} not provided.")
        return total_value
    
