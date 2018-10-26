from app.models import OrderModel, db
from mvc.models import Order, Client
from bmex import BmexClient


class OrderBmex(Order):

    def update(self, order_response: dict):
        self.symbol = order_response.get('symbol')
        self.amount = order_response.get('amount')
        self.price = order_response.get('price')
        self.side = order_response.get('side')
        self.type = order_response.get('type')
        try:
            self.type = self.type.lower()
        except:
            pass


class ClientBmex(Client):

    def create_order(self):
        order = OrderModel(self.api.order['id'], self.client_object.id)
        self.client_object.orders.append(order)
        db.session.add(self.client_object)
        db.session.commit()
        self.orders.append(OrderBmex(order))

    def get_balance(self):
        self.balance = self.api.balance

    def update_orders(self):
        for order in self.orders:
            order.update(self.api.orders[order.id])

    def load_api(self, key: str, secret: str):
        self.api = BmexClient(key, secret)

    def load_orders(self, orders_objects):
        self.orders = [OrderBmex(order_object) for order_object in orders_objects]
