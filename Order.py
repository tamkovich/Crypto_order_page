import ccxt.async_support as ccxt

round_ = lambda x: round(float(x) * 2) / 2


class Client:

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

    def __init__(self, apiKey, secret, failed=False, balance=0, order_id=None, order_exist=None,
                 amount=0, open=0, side=None, order_type=None):
        self.apiKey = apiKey
        self.secret = secret
        self.symbol = 'BTC/USD'
        self.failed = failed
        self.balance = balance
        self.order = None
        self.order_id = order_id
        self.order_exist = order_exist
        self.amount = amount
        self.open = open
        self.side = side
        self.order_type = order_type
        self.auth = True
        self.exchange = ccxt.bitmex({
            'apiKey': apiKey,
            'secret': secret,
            'timeout': 30000,
            'enableRateLimit': True,
        })

        if self.test_mode:
            if 'test' in self.exchange.urls:
                self.exchange.urls['api'] = self.exchange.urls['test']

    async def get_balance(self):
        balance = None
        if self.auth:
            auth = True
            try:
                balance = await self.exchange.fetch_balance()
            except ccxt.AuthenticationError:
                print(f'Auth error')
                auth = False
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                print(f'Failed to check order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
            self.auth = auth
            self.balance = balance["BTC"]["total"]
            if balance["BTC"]["used"]:
                self.order_exist = True
            else:
                self.order_exist = False
                self.amount = 0
                self.open = 0
                self.side = 'null'
                self.order_id = 'null'
                self.order_type = 'null'

    def _push_order_fields(self):
        self.amount = self.order.get("amount")
        self.open = self.order.get("price")
        self.side = self.order.get("side")
        self.order_id = self.order.get("id")
        self.order_type = self.order_types.get(self.order.get("type"))
        print(self.order.get("type"))

    def table_data(self):
        return {
            "balance": self.balance,
            "order_type": self.order_type,
            "symbol": self.symbol,
            "amount": self.amount,
            "open": self.open,
            "side": self.side,
            "liquidation": None,   # не найдено
            "failed": self.failed,
            "order_id": self.order_id,
            "order_exist": self.order_exist,
        }

    def _debug(self, filename, params={}):
        if self.debug_mode:
            with open(f'{self.debug_files_path}{filename}_{self.apiKey}.txt', 'w') as f:
                for k in params.keys():
                    f.write(f'{k} = {params[k]}\n')

    async def _create_order(self, order_type, side, amount, price=None, params={}):
        order = {}
        price = round_(price) if price else None
        if self.auth:
            auth = True
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
                auth = False
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                self.failed = True
                print(f'Failed to create order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
            self.auth = auth
        self.order = order
        self._push_order_fields()
        self._debug(f'create_{self.order_type}_order', {'order': self.order})
        await self.get_balance()
        await self.exchange.close()

    async def create_market_order(self, side, amount=10.0):
        await self._create_order('Market', side, amount)

    async def create_stop_order(self, side, amount, stopPx):
        params = {"stopPx": round_(stopPx)}
        await self._create_order("Stop", side, amount, params=params)

    async def create_limit_order(self, side, amount, price):
        await self._create_order("Limit", side, amount, price)

    async def check_order(self):
        if self.order_exist:
            order = {}
            auth = True
            for _ in range(self.retry):
                auth = True
                try:
                    order = await self.exchange.fetch_order(id=self.order_id, symbol=self.symbol)
                    break
                except ccxt.OrderNotFound:
                    print("Order not found")
                except ccxt.AuthenticationError:
                    print(f'Auth error')
                    auth = False
                except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                    print(f'Failed to check order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
            self.auth = auth
            self.order = order
            self._push_order_fields()
        else:
            self.order = {}
        self._debug('check_order', {'order': self.order})
        await self.get_balance()
        await self.exchange.close()

    async def _close_order(self):
        order = {}
        if self.auth:
            auth = True
            try:
                order = await self.exchange.cancel_order(self.order_id, self.symbol)
            except ccxt.AuthenticationError:
                print(f'Auth error')
                auth = False
            self.auth = auth
        self.order = {}
        self._debug('_close_order', {'order': self.order, 'response': order})

    async def rm_all_orders(self):
        orders = await self.exchange.fetch_open_orders(self.symbol)
        if orders:
            for order in orders:
                self.order_id = order['id']
                await self._close_order()
        else:
            self.order = {}
        self._debug('rm_all_orders', {'order': self.order, 'orders': orders, 'order_exist': self.order_exist})
        await self.get_balance()
        await self.exchange.close()

    @staticmethod
    def check_if_already_exist(clients, new_client):
        for client in clients:
            if client.secret == new_client['secret'] and client.apiKey == new_client['apiKey']:
                return False
        return True


def _is_field_not_blank(field, *filters):
    b = False
    if field is not None:
        b = True
        for f in filters:
            if field == f:
                b = False
                break
    return b


def update_client_data(client, data):
    res = {
        "balance": client.balance,
        "order_type": client.order_type,
        "symbol": client.symbol,
        "amount": client.amount,
        "open": client.open,
        "side": client.side,
        "liquidation": client.liquidation,  # не найдено
        "failed": client.failed,
        "order_exist": client.order_exist,
        "order_id": client.order_id,
    }
    if _is_field_not_blank(data['balance']):
        client.balance = data['balance']
        res['balance'] = data['balance']
    if _is_field_not_blank(data['order_type']):
        client.order_type = data['order_type']
        res['order_type'] = data['order_type']
    if _is_field_not_blank(data['symbol']):
        client.symbol = data['symbol']
        res['symbol'] = data['symbol']
    if _is_field_not_blank(data['amount']):
        client.amount = data['amount']
        res['amount'] = data['amount']
    if _is_field_not_blank(data['open']):
        client.open = data['open']
        res['open'] = data['open']
    if _is_field_not_blank(data['side']):
        client.side = data['side']
        res['side'] = data['side']
    if _is_field_not_blank(data['liquidation']):
        client.liquidation = data['liquidation']
        res['liquidation'] = data['liquidation']
    if _is_field_not_blank(data['failed']):
        client.failed = data['failed']
        res['failed'] = data['failed']
    if _is_field_not_blank(data['order_exist']):
        client.order_exist = data['order_exist']
        res['order_exist'] = data['order_exist']
    if _is_field_not_blank(data['order_id']):
        client.order_id = data['order_id']
        res['order_id'] = data['order_id']
    return res


def check_for_blank_in_json_by_fields(data, *args):
    for _key in args:
        if not _is_field_not_blank(data.get(_key), '', 0, '0'):
            return False, f'Invalid data with field {_key}'
    return True, None
