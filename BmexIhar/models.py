from app.models import OrderModel, db
from mvc.models import Order, Client
from bmex import BmexClient

from loggers import get_logger

logger = get_logger('BmexIhar.models')


class OrderBmex(Order):

    def update(self, order_response: dict):
        logger.info(f'OrderBmex.update {order_response}')
        self.symbol = order_response.get('symbol')
        self.amount = order_response.get('amount')
        self.price = order_response.get('price')
        self.side = order_response.get('side')
        self.type = order_response.get('type')
        try:
            self.type = self.type.lower()
        except:
            pass
        self.liquidation = order_response.get('liquidationPrice')
        self.leverage = order_response.get('leverage')


class ClientBmex(Client):

    def create_order(self):
        if self.api.failed:
            logger.info('ClientBmex.create_order api failed')
        else:
            logger.info(f'ClientBmex.create_order api order {self.api.order["id"]}')
            order = OrderModel(order_exchange_id=self.api.order['id'], client=self.client_object)
            db.session.add(order)
            db.session.commit()
            self.orders.append(OrderBmex(order))

    def get_balance(self):
        self.balance = self.api.balance

    def update_orders(self):
        for order in self.orders:
            order.update(self.api.orders[order.id])
        self.positions = [OrderBmex(position_object) for position_object in self.api.positions]
        for i, position in enumerate(self.positions):
            position.update(self.api.positions[i])

    def load_api(self, key: str, secret: str, email: str):
        self.api = BmexClient(key, secret, email)

    def load_orders(self, orders_objects):
        self.orders = [OrderBmex(order_object) for order_object in orders_objects]
