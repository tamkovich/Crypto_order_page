import sqlalchemy.exc
import asyncio
import time


from app.models import ClientModel, db
from BmexIhar.models import ClientBmex
from mvc.views import Table

from private.redis_conn import r
from loggers import get_logger

logger = get_logger('BmexIhar.views')

_round = lambda x: None if x is None else round(x, 1)


class TableIhar(Table):

    col_orders = 3
    failed_data = {'amount': '', 'price': '', 'type': ''}

    @staticmethod
    def _gen_order_structure(side, price, amount):
        return {
            'side': side,
            'price': price,
            'amount': amount,
        }

    @staticmethod
    def _gen_position_structure(side, price, amount, leverage, liquidation):
        return {
            'side': side,
            'price': price,
            'amount': amount,
            'leverage': leverage,
            'liquidation': liquidation,
        }

    def _get_balance(self, *args, **kwargs):
        for client in self.clients:
            client.api.redis_get_balance()

    def add_client(self, key: str, secret: str):
        self.error_msg = ''
        try:
            client_object = ClientModel(key, secret)
            db.session.add(client_object)
            db.session.commit()
            r.set('client_id', client_object.id)
            self.clients.append(ClientBmex(client_object))
            self.update_clients_info()
            for client in self.clients:
                similar_clients = ClientModel.query.filter_by(email=client.client_object.email, visible=True).all()
                if len(similar_clients):
                    for i in range(len(similar_clients)-1):
                        similar_clients[i].visible = False
                        self.error_msg = 'already exist!'
                    db.session.commit()
            self.clients = list(filter(lambda c: c.client_object.visible, self.clients))
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            cl = ClientModel.query.filter_by(apiKey=key, secret=secret, visible=False).first()
            if cl:
                cl.visible = True
                db.session.commit()
                self.clients.append(ClientBmex(cl))
                r.set('client_id', cl.id)
                self.update_clients_info()
                for client in self.clients:
                    similar_clients = ClientModel.query.filter_by(email=client.client_object.email, visible=True).all()
                    if len(similar_clients):
                        for i in range(len(similar_clients) - 1):
                            similar_clients[i].visible = False
                            self.error_msg = 'already exist!'
                        db.session.commit()
                self.clients = list(filter(lambda c: c.client_object.visible, self.clients))
            else:
                self.error_msg = 'already exist!'

    def set_unvisible_client(self, data: dict):
        for i, client in enumerate(self.clients):
            if client.client_object.id == int(data['client_id']):
                client.client_object.visible = False
                r.set('unvisible_client_id', client.client_object.id)
                cl = ClientModel.query.filter_by(id=client.client_object.id).first()
                cl.visible = False
                db.session.commit()
                _ = self.clients.pop(i)
                break

    def update_clients_info(self):
        async_loop = load_event_loop()
        tasks = [async_loop.create_task(client.api.update_user_info()) for client in self.clients]
        run_event_loop(async_loop, tasks)

        for client in self.clients:
            if client.api.email is not None and client.api.email != client.client_object.email:
                client.email = client.api.email
                client.client_object.email = client.api.email
                db.session.commit()

    def add_order(self, **kwargs):
        async_loop = load_event_loop()
        valid_price = self.check_price(async_loop, kwargs)
        tasks = []
        self._get_balance()
        balance = sum(c.balance.get('walletBalance', 0) for c in self.clients)
        if valid_price:
            for client in self.clients:
                # compute amount by share in balance
                amount = int((client.balance.get('walletBalance', 0) / balance) * int(kwargs['amount'])) if kwargs['amount'] is not None else None
                order_kwargs = self._gen_order_structure(kwargs['side'], kwargs['price'], amount)
                order_kwargs['type'] = kwargs['type']
                tasks.append(async_loop.create_task(client.api.create_order(**order_kwargs)))
            run_event_loop(async_loop, tasks)

            for client in self.clients:
                client.create_order()

    def add_failed_order(self, **kwargs):
        async_loop = load_event_loop()
        tasks = []
        self._get_balance()
        balance = sum(c.balance.get('walletBalance', 0) if c.api.failed else 0 for c in self.clients)
        for client in self.clients:
            if client.api.failed:
                client.api.failed = False
                # compute amount by share in balance
                amount = int((client.balance.get('walletBalance', 0) / balance) * int(kwargs['amount'])) if kwargs['amount'] is not None else None
                order_kwargs = self._gen_order_structure(kwargs['side'], kwargs['price'], amount)
                order_kwargs['type'] = kwargs['type']
                tasks.append(async_loop.create_task(client.api.create_order(**order_kwargs)))
        run_event_loop(async_loop, tasks)

    def update_all(self):
        async_loop = load_event_loop()
        tasks = []
        for client in self.clients:
            orders_ids = list(map(lambda o: o.id, client.orders))
            client.api.redis_check_everything(orders_ids)
            # tasks.append(async_loop.create_task(client.api.check_everything(orders_ids)))
        # run_event_loop(async_loop, tasks)
        tasks = []
        self._get_balance()
        pending = asyncio.Task.all_tasks()
        run_event_loop(async_loop, asyncio.gather(*pending), preload=True)
        for client in self.clients:
            client.update_orders()
            client.get_balance()

    def view(self):
        self.marginBalance = 0
        self.walletBalance = 0
        self.amount = 0
        self.failed_data = {'amount': '', 'price': '', 'type': ''}
        self.table_data = dict()
        for i, client in enumerate(self.clients):
            self.table_data[i] = dict()
            self.table_data[i]['id'] = client.client_object.id
            self.table_data[i]['username'] = client.api.email
            self.table_data[i]['walletBalance'] = round(client.balance.get('walletBalance', 0), 4)
            self.table_data[i]['marginBalance'] = round(client.balance.get('marginBalance', 0), 4)
            self.table_data[i]['limits'] = [None] * self.col_orders
            self.table_data[i]['stops'] = [None] * self.col_orders
            limits = list(filter(lambda o: o.type == 'limit', client.orders))[:self.col_orders]
            stops = list(filter(lambda o: o.type == 'stop', client.orders))[:self.col_orders]
            self.walletBalance += client.balance.get('walletBalance', 0)
            self.marginBalance += client.balance.get('marginBalance', 0)
            for _j in range(self.col_orders):
                # limit
                try:
                    self.table_data[i]['limits'][_j] = self._gen_order_structure(
                        limits[_j].side, limits[_j].price, limits[_j].amount
                    )
                except IndexError:
                    self.table_data[i]['limits'][_j] = self._gen_order_structure(None, None, None)
                # stop
                try:
                    self.table_data[i]['stops'][_j] = self._gen_order_structure(
                        stops[_j].side, stops[_j].price, stops[_j].amount
                    )
                except IndexError:
                    self.table_data[i]['stops'][_j] = self._gen_order_structure(None, None, None)

            self.table_data[i]['positions'] = []
            for position in client.positions:
                self.table_data[i]['positions'].append(self._gen_position_structure(
                    position.side,
                    _round(position.price),
                    position.amount,
                    round(position.leverage, 2),
                    _round(position.liquidation),
                ))
                self.amount += abs(position.amount)
        self._compose_failed()

    def _compose_failed(self):
        amount = 0
        price = 0
        order_type = 'active'  # for the active order form
        for client in self.clients:
            if client.api.failed:
                amount += client.api.order.get('amount', 0)
                price = client.api.order.get('price', 0)
                order_type = client.api.order.get('order_type', '')
                #print(client.api.order)
        self.failed_data['amount'] = amount
        self.failed_data['price'] = price
        self.failed_data['type'] = order_type.capitalize()

    def gen_data(self):
        response = {
            'data': self.table_data,
            'count': len(self.table_data),
            'marginBalance': round(self.marginBalance, 4),
            'walletBalance': round(self.walletBalance, 4),
            'failed_data': self.failed_data,
            'amount': self.amount,
        }
        logger.info(f'RETURN {response}')
        return response

    def check_price(self, async_loop, kwargs):
        self.error_msg = ''
        tasks = [async_loop.create_task(self.clients[0].api.current_price(**kwargs))]
        run_event_loop(async_loop, tasks)
        if self.clients[0].api.invalid_price:
            self.error_msg = 'Invalid Price'
            return False
        return True

    def close_all_orders(self):
        async_loop = load_event_loop()
        tasks = [async_loop.create_task(client.api.rm_all_orders()) for client in self.clients]
        run_event_loop(async_loop, tasks)

    def close_all_positions(self):
        async_loop = load_event_loop()
        tasks = [async_loop.create_task(client.api.rm_all_positions()) for client in self.clients]
        run_event_loop(async_loop, tasks)

    def load_clients(self, clients_objects):
        self.clients = []
        for client_object in clients_objects:
            if client_object.visible and client_object.email != 'autherror@email':
                self.clients.append(ClientBmex(client_object))


def load_event_loop():
    """
    creates an event loop.
    If a few loops already running it will sleep for a 3 seconds to wait
    his chance to set a new event loop
    :return: [asyncio] async_loop
    """
    while True:
        try:
            async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(async_loop)
            return async_loop
        except:
            time.sleep(3)


def run_event_loop(async_loop, tasks, preload=False):
    """
    runs event loop, just when it will be possible and none of other loops existing
    :param async_loop: event loop which have to be execute
    :param tasks: tasks which event loop will run
    :param preload: <bool> False by default if func gets only list of tasks. True if wait tasks or gather tasks
    :return: None
    """
    if tasks:
        wait_tasks = tasks if preload else asyncio.wait(tasks)
        while True:
            try:
                async_loop.run_until_complete(wait_tasks)
                break
            except RuntimeError:
                time.sleep(3)
