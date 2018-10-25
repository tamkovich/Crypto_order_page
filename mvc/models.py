from abc import ABC, abstractmethod


class Order(ABC):

    def __init__(self, id: str, symbol: str):
        self.id = id
        self.symbol = symbol

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def cancel_order(self):
        pass


class Client(ABC):

    exchange = None

    def __init__(self, key: str, secret: str, orders: list):
        self.orders = orders
        self.load_exchange(key, secret)

    @abstractmethod
    def create_order(self):
        pass

    @abstractmethod
    def get_balance(self):
        pass

    @abstractmethod
    def update_orders(self):
        pass

    @abstractmethod
    def load_exchange(self, key: str, secret: str):
        pass
