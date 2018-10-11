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
    retry = 3
    debug_mode = True
    debug_files_path = 'debug/'

    def __init__(self, apiKey, secret, test_mode=True):
        self.apiKey = apiKey
        self.secret = secret
        self.test_mode = test_mode
        self.symbol = 'BTC/USD'  # change for your symbol
        self.response = None

        self.failed = False      # 'True' if order not created

        self.current_order = None
        # править нельзя
        self.balance = None      # Cash баланс счета (=баланс по закрытым позициям)
        self.order_type = None  # Market , Limit, Stop
        self.side = None         # Открытая позиция по счету (символ)
        self.contracts = None    # Открытая позиция по счету (количество контрактов)
        self.open = None         # Открытая позиция по счету (цена входа)
        self.liquidation = None  # Открытая позиция по счету (ликвидационная цена)

        self.current_order_exist = None
        self.current_order_id = None

        self.exchange = ccxt.bitmex({
            'apiKey': apiKey,
            'secret': secret,
            'timeout': 30000,
            'enableRateLimit': True,
        })

        if self.test_mode:
            if 'test' in self.exchange.urls:
                self.exchange.urls['api'] = self.exchange.urls['test']  # ←----- switch the base URL to testnet

    async def create_market_order(self, side, amount=1.0):
        # create-order --- socket
        response = None
        try:
            # Market
            response = await self.exchange.create_order(self.symbol, 'Market', side, amount)
            self.side = side
            self.order_type = 0
            self.failed = False
        except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
            self.failed = True
            print(f'Failed to create order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
        self.response = response
        if self.debug_mode:
            with open(f'{self.debug_files_path}create_market_order.txt_{self.apiKey}', 'w') as f:
                f.write(f'response = {self.response}')
        await self.gen_data()

    async def gen_data(self):
        # create-order --- socket
        # add-client --- socket
        # reload-table --- socket
        await self.get_current_position()
        await self.exchange.close()

    def get_table_data(self):
        # create-order --- socket
        # add-client --- socket
        # reload-table --- socket
        return {
            "apiKey": self.apiKey,
            "balance": self.balance or 0,
            "order_type": self.order_types.get(self.order_type),
            "symbol": self.symbol,
            "contracts": self.contracts or 0,
            "open": self.open or 0,
            "side": self.side,
            "liquidation": self.liquidation or 0,  # не найдено
            "failed": self.failed,
            "current_order_exist": self.current_order_exist,
            "current_order_id": self.current_order_id,
        }

    async def get_current_position(self):
        # create-order --- socket
        # add-client --- socket
        # reload-table --- socket
        print('here')
        orders = await self.exchange.fetch_orders()
        self.current_order = orders[-1]
        self.current_order_id = self.current_order['id']
        await self._check_order(self.current_order_id, self.symbol)
        self._gen_current_order_data()
        await self.get_balance()
        if self.debug_mode:
            with open(f'{self.debug_files_path}get_current_position_{self.apiKey}.txt', 'w') as f:
                f.write(f'current_order = {self.current_order}\n'
                        f'current_order_id = {self.current_order_id}')

    def _gen_current_order_data(self):
        # create-order --- socket
        # add-client --- socket
        # reload-table --- socket
        try:
            self.order_type = self.current_order["type"]
            self.contracts = self.current_order["amount"]
            self.open = self.current_order["price"]
            self.side = self.current_order["side"]
            self.current_order_id = self.current_order["id"]
            self.current_order_exist = True
        except:
            self.current_order_exist = False

    async def get_balance(self):
        # create-order --- socket
        # add-client --- socket
        # reload-table --- socket
        balance = await self.exchange.fetch_balance()
        self.balance = balance['total']['BTC']

    async def _check_order(self, order_id, symbol):
        # create-order --- socket
        order = None
        for _ in range(self.retry):
            try:
                order = await self.exchange.fetch_order(id=order_id, symbol=symbol)
                break
            except ccxt.OrderNotFound:
                print("Order not found")
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                print(f'Failed to check order with {self.exchange.id} {type(_ex).__name__} {str(_ex)}')
        self.current_order = order
        if self.debug_mode:
            with open(f'{self.debug_files_path}_check_order_{self.apiKey}.txt', 'w') as f:
                f.write(f'current_order = {self.current_order}')
        return order

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
        "contracts": client.contracts,
        "open": client.open,
        "side": client.side,
        "liquidation": client.liquidation,  # не найдено
        "failed": client.failed,
        "current_order_exist": client.current_order_exist,
        "current_order_id": client.current_order_id,
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
    if _is_field_not_blank(data['contracts']):
        client.contracts = data['contracts']
        res['contracts'] = data['contracts']
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
    if _is_field_not_blank(data['current_order_exist']):
        client.current_order_exist = data['current_order_exist']
        res['current_order_exist'] = data['current_order_exist']
    if _is_field_not_blank(data['current_order_id']):
        client.current_order_id = data['current_order_id']
        res['current_order_id'] = data['current_order_id']
    return res
