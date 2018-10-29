import ccxt.async_support as ccxt

round_ = lambda x: round(float(x) * 2) / 2


class BmexClient:

    order_types = {
        0: 'Market',
        1: 'Stop',
        2: 'Limit',
        'Market': 'Market',
        'market': 'Market',
        'Stop': 'Stop',
        'stop': 'Stop',
        'Limit': 'Limit',
        'limit': 'Limit',
    }
    retry = 3
    debug_mode = True
    debug_files_path = 'debug/'
    test_mode = True

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret
        self.symbol = 'BTC/USD'
        self.failed = False
        self.balance = 0
        self.order = {}
        self.exchange = None
        self.orders = dict()

    def load_exchange(self):
        self.exchange = ccxt.bitmex({
            'apiKey': self.key,
            'secret': self.secret,
            'timeout': 30000,
            'enableRateLimit': True,
        })

        if self.test_mode:
            if 'test' in self.exchange.urls:
                self.exchange.urls['api'] = self.exchange.urls['test']
        self.exchange.open()

    async def get_balance(self):
        self.load_exchange()
        balance = None
        for _ in range(self.retry):
            try:
                balance = await self.exchange.fetch_balance()
                break
            except ccxt.AuthenticationError:
                print(f'Auth error')
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                print(f'Failed to check order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
        self.balance = balance["BTC"]["total"]
        await self.exchange.close()

    def _debug(self, filename, params={}):
        if self.debug_mode:
            with open(f'{self.debug_files_path}{filename}_{self.key}.txt', 'w') as f:
                for k in params.keys():
                    f.write(f'{k} = {params[k]}\n')

    async def _create_order(self, order_type, side, amount, price=None, params={}):
        order = {}
        price = round_(price) if price else None
        try:
            order = await self.exchange.create_order(
                symbol=self.symbol,
                type=order_type,
                side=side,
                amount=int(amount),
                price=price,
                params=params,
            )
            self.failed = False
        except ccxt.AuthenticationError:
            print(f'Auth error')
        except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
            self.failed = True
            print(f'Failed to create order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
        except Exception as e:
            print(e)
            self.failed = True
        self.order = order
        self._debug(f'create_{self.order.get("type")}_order', {'order': self.order})

    async def create_order(self, type, side, amount, price=None):
        self.load_exchange()
        assert type in ['Stop', 'Market', 'Limit'], 'There is no such order-type. ' \
                                                    'Valid order types: [Stop, Market, Limit]'
        if type == 'Stop':
            params = {"stopPx": round_(price)}
            await self._create_order(type, side, amount, params=params)
        else:
            await self._create_order(type, side, amount, price)
        await self.exchange.close()

    async def _close_order(self, order_id: str):
        order = {}
        try:
            order = await self.exchange.cancel_order(order_id, self.symbol)
        except ccxt.AuthenticationError:
            print(f'Auth error')
        self.order = {}
        self._debug('_close_order', {'order': self.order, 'response': order})

    async def rm_all_orders(self):
        self.load_exchange()
        orders = await self.exchange.fetch_open_orders(self.symbol)
        if orders:
            for order in orders:
                await self._close_order(order['id'])
        else:
            self.order = {}
        self._debug('rm_all_orders', {'order': self.order, 'orders': orders})
        await self.exchange.close()

    async def check_all_orders(self, orders_ids: list):
        self.load_exchange()
        for order_id in orders_ids:
            self.orders[order_id] = dict()
        orders = []
        for _ in range(self.retry):
            try:
                orders = await self.exchange.fetch_open_orders(self.symbol)
            except ccxt.OrderNotFound:
                print("Order not found")
            except ccxt.AuthenticationError:
                print(f'Auth error')
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                print(f'Failed to check order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
            except Exception as _ex:
                print(f'Something goes wrong with {order_id}')
        for order in orders:
            if order['id'] in orders_ids:
                self.orders[order['id']] = order
        assert len(self.orders) == len(orders_ids), 'Length of orders you have not the same as in exchange'
        await self.exchange.close()


def _is_field_not_blank(field, *filters):
    b = False
    if field is not None:
        b = True
        for f in filters:
            if field == f:
                b = False
                break
    return b


def check_for_blank_in_json_by_fields(data: dict, *args):
    for _key in args:
        if not _is_field_not_blank(data.get(_key), '', 0, '0'):
            return False, f'Invalid data with field {_key}'
    return True, None
