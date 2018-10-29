import asyncio

from app.models import ClientModel, db
from BmexIhar.models import ClientBmex
from mvc.views import Table


class TableIhar(Table):

    col_orders = 3
    order_structure_data = {'side': None, 'price': None, 'amount': None}

    @staticmethod
    def _gen_order_structure(side, price, amount):
        return {
            'side': side,
            'price': price,
            'amount': amount,
        }

    def add_client(self, key: str, secret: str):
        client_object = ClientModel(key, secret)
        db.session.add(client_object)
        db.session.commit()
        self.clients.append(ClientBmex(client_object))

    def add_order(self, **kwargs):
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
        tasks = []
        for client in self.clients:
            # client.api.load_exchange()
            tasks.append(async_loop.create_task(client.api.create_order(**kwargs)))
        wait_tasks = asyncio.wait(tasks)
        async_loop.run_until_complete(wait_tasks)
        for client in self.clients:
            client.create_order()

    def update_all(self):
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
        tasks = []
        for client in self.clients:
            # client.api.load_exchange()
            orders_ids = list(map(lambda o: o.id, client.orders))
            tasks.append(async_loop.create_task(client.api.check_all_orders(orders_ids)))
        if tasks:
            wait_tasks = asyncio.wait(tasks)
            async_loop.run_until_complete(wait_tasks)
            tasks = []
        for client in self.clients:
            # client.api.load_exchange()
            tasks.append(async_loop.create_task(client.api.get_balance()))
        if tasks:
            wait_tasks = asyncio.wait(tasks)
            async_loop.run_until_complete(wait_tasks)
        for client in self.clients:
            client.update_orders()
            client.get_balance()

    def view(self):
        self.balance = 0
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

    def close_all_orders(self):
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
        tasks = [async_loop.create_task(client.api.rm_all_orders()) for client in self.clients]
        wait_tasks = asyncio.wait(tasks)
        async_loop.run_until_complete(wait_tasks)

    def load_clients(self, clients_objects):
        self.clients = [ClientBmex(client_object) for client_object in clients_objects]
