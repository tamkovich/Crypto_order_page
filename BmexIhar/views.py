import asyncio
import time

from app.models import ClientModel, db
from BmexIhar.models import ClientBmex
from mvc.views import Table


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

    def _get_balance(self, async_loop, tasks):
        for client in self.clients:
            tasks.append(async_loop.create_task(client.api.get_balance()))
        if tasks:
            wait_tasks = asyncio.wait(tasks)
            run_event_loop(async_loop, wait_tasks)
            tasks = []
        return tasks

    def add_client(self, key: str, secret: str):
        client_object = ClientModel(key, secret)
        db.session.add(client_object)
        db.session.commit()
        self.clients.append(ClientBmex(client_object))

    def add_order(self, **kwargs):
        async_loop = load_event_loop()
        tasks = []
        tasks = self._get_balance(async_loop, tasks)
        balance = sum(c.balance for c in self.clients)
        for client in self.clients:
            # compute amount by share in balance
            amount = int((client.balance / balance) * int(kwargs['amount'])) if kwargs['amount'] is not None else None
            order_kwargs = self._gen_order_structure(kwargs['side'], kwargs['price'], amount)
            order_kwargs['type'] = kwargs['type']
            tasks.append(async_loop.create_task(client.api.create_order(**order_kwargs)))
        wait_tasks = asyncio.wait(tasks)
        run_event_loop(async_loop, wait_tasks)

        for client in self.clients:
            client.create_order()

    def add_failed_order(self, **kwargs):
        async_loop = load_event_loop()
        tasks = []
        tasks = self._get_balance(async_loop, tasks)
        balance = sum(c.balance if c.api.failed else 0 for c in self.clients)
        for client in self.clients:
            if client.api.failed:
                client.api.failed = False
                # compute amount by share in balance
                amount = int((client.balance / balance) * int(kwargs['amount'])) if kwargs['amount'] is not None else None
                order_kwargs = self._gen_order_structure(kwargs['side'], kwargs['price'], amount)
                order_kwargs['type'] = kwargs['type']
                tasks.append(async_loop.create_task(client.api.create_order(**order_kwargs)))
        if tasks:
            wait_tasks = asyncio.wait(tasks)
            run_event_loop(async_loop, wait_tasks)

    def update_all(self):
        async_loop = load_event_loop()
        tasks = []
        for client in self.clients:
            orders_ids = list(map(lambda o: o.id, client.orders))
            tasks.append(async_loop.create_task(client.api.check_everything(orders_ids)))
        if tasks:
            wait_tasks = asyncio.wait(tasks)
            run_event_loop(async_loop, wait_tasks)
            tasks = []
        _ = self._get_balance(async_loop, tasks)
        pending = asyncio.Task.all_tasks()
        run_event_loop(async_loop, asyncio.gather(*pending))
        for client in self.clients:
            client.update_orders()
            client.get_balance()

    def view(self):
        self.balance = 0
        self.failed_data = {'amount': '', 'price': '', 'type': ''}
        for i, client in enumerate(self.clients):
            self.table_data[i] = dict()
            self.table_data[i]['balance'] = client.balance
            self.table_data[i]['limits'] = [None] * self.col_orders
            self.table_data[i]['stops'] = [None] * self.col_orders
            limits = list(filter(lambda o: o.type == 'limit', client.orders))[:self.col_orders]
            stops = list(filter(lambda o: o.type == 'stop', client.orders))[:self.col_orders]
            self.balance += self.table_data[i]['balance']
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
                    position.price,
                    position.amount,
                    position.leverage,
                    position.liquidation
                ))
        self._compose_failed()

    def _compose_failed(self):
        amount = 0
        price = 0
        order_type = 'active'  # for the active order form
        for client in self.clients:
            if client.api.failed:
                amount += client.api.order.get('amount', 0)
                price = client.api.order['price']
                order_type = client.api.order['order_type']
                print(client.api.order)
        self.failed_data['amount'] = amount
        self.failed_data['price'] = price
        self.failed_data['type'] = order_type.capitalize()

    def gen_data(self):
        return {
            'data': self.table_data,
            'count': len(self.table_data),
            'balance': self.balance,
            'failed_data': self.failed_data,
        }

    def close_all_orders(self):
        async_loop = load_event_loop()
        tasks = [async_loop.create_task(client.api.rm_all_orders()) for client in self.clients]
        wait_tasks = asyncio.wait(tasks)
        run_event_loop(async_loop, wait_tasks)

    def load_clients(self, clients_objects):
        self.clients = [ClientBmex(client_object) for client_object in clients_objects]


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


def run_event_loop(async_loop, wait_tasks):
    """
    runs event loop, just when it will be possible and none of other loops existing
    :param async_loop: event loop which have to be execute
    :param wait_tasks: tasks which event loop will run
    :return: None
    """
    while True:
        try:
            async_loop.run_until_complete(wait_tasks)
            break
        except RuntimeError:
            time.sleep(3)
