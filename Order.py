import ccxt.async_support as ccxt


class Client:

    order_types = {
        0: 'Market',
        1: 'Limit',
        2: 'Stop',
        3: 'StopLimit',
        4: 'LimitIfTouched',  # take profit limit
        'Market': 'Market',
        'Limit': 'Limit',
        'Stop': 'Stop',
        'StopLimit': 'StopLimit',
        'LimitIfTouched': 'LimitIfTouched',  # take profit limit
        'market': 'Market',
    }
    sides = {'sell': 'buy', 'buy': 'sell'}
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
        balance = await self.exchange.fetch_balance()
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

    async def create_market_order(self, side, amount=10.0):
        order = {}
        try:
            order = await self.exchange.create_order(self.symbol, 'Market', side, amount)
            self.failed = False
        except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
            self.failed = True
            print(f'Failed to create order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
        self.order = order
        if self.debug_mode:
            with open(f'{self.debug_files_path}create_market_order.txt_{self.apiKey}', 'w') as f:
                f.write(f'order = {self.order}')
        self._push_order_fields()
        await self.get_balance()
        await self.exchange.close()

    async def check_order(self):
        if self.order_exist:
            order = None
            for _ in range(self.retry):
                try:
                    order = await self.exchange.fetch_order(id=self.order_id, symbol=self.symbol)
                    break
                except ccxt.OrderNotFound:
                    print("Order not found")
                except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                    print(f'Failed to check order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
                except:
                    print(f'just another problem with {self.exchange.id} ,'
                          f' order_id = {self.order_id} and symbol = {self.symbol}')
            self.order = order
            self._push_order_fields()
        if self.debug_mode:
            with open(f'{self.debug_files_path}check_order_{self.apiKey}.txt', 'w') as f:
                f.write(f'order = {self.order}')
        await self.get_balance()
        await self.exchange.close()

    async def close_order(self):
        if self.order_types.get(self.order_type) == 'Market' and self.order_exist:
            await self.create_market_order(self.sides[self.side], self.amount)
            self.order["amount"] = 0
        else:
            order = await self.exchange.cancel_order(self.order_id, self.symbol)
        self.order = None
        self.order_id = None
        if self.debug_mode:
            with open(f'{self.debug_files_path}close_order_{self.apiKey}.txt', 'w') as f:
                f.write(f'order = {self.order} \n'
                        f'res = {order}')
        await self.get_balance()
        await self.exchange.close()

    @staticmethod
    def check_if_already_exist(clients, new_client):
        # add-client --- socket
        for client in clients:
            if client.secret == new_client['secret'] and client.apiKey == new_client['apiKey']:
                return False
        return True


def _is_field_not_blank(field, filters=''):
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
