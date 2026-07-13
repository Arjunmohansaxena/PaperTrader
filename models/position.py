class Position:

    def __init__(self,symbol,quantity:int,avg_buy_price:float):
        self.symbol = symbol
        self.quantity = quantity
        self.avg_buy_price = avg_buy_price

    def add_share(self,quantity:int,price:float):
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        self.avg_buy_price = (self.avg_buy_price * self.quantity + price * quantity) / (self.quantity + quantity)
        self.quantity += quantity
    
    def remove_share(self,quantity:int):
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if quantity > self.quantity:
            raise ValueError("Cannot remove more shares than currently held.")
        self.quantity -= quantity
    
    def get_position_value(self,current_price:float):
        return self.quantity * current_price    
    
    def unrealized_profit_loss(self,current_price:float):
        return (current_price - self.avg_buy_price) * self.quantity
    
    