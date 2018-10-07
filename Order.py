import ccxt.async_support as ccxt


class Client:

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
        self.side = None         # Открытая позиция по счету (символ)
        self.contracts = None    # Открытая позиция по счету (количество контрактов)
        self.open = None         # Открытая позиция по счету (цена входа)
        self.liquidation = None  # Открытая позиция по счету (ликвидационная цена)

        self.exchange = ccxt.bitmex({
            'apiKey': apiKey,
            'secret': secret,
            'timeout': 30000,
            'enableRateLimit': True,
        })

        if self.test_mode:
            if 'test' in self.exchange.urls:
                self.exchange.urls['api'] = self.exchange.urls['test']  # ←----- switch the base URL to testnet

    def get_table_data(self):
        return {
            "apiKey": self.apiKey,
            "balance": self.balance,
            "symbol": self.symbol,
            "contracts": self.contracts,
            "open": self.open,
            "side": self.side,
            "liquidation": self.liquidation,  # не найдено
        }

    def _gen_current_order_data(self):
        # self.symbol = self.symbol
        try:
            self.contracts = self.current_order["amount"]
            self.open = self.current_order["price"]
            self.side = self.current_order["side"]
        except:
            pass

    async def gen_data(self):
        # get_current_position
        await self.get_current_position()
        # get_balance
        # await self.get_balance()
        await self.exchange.close()

    async def get_balance(self):
        balance = await self.exchange.fetch_balance()
        self.balance = balance['total']['BTC']

    async def create_market_order(self, side, amount=1.0):
        response = None
        try:
            # Market
            response = await self.exchange.create_order(self.symbol, 'Market', side, amount)
            self.side = side  # if side still will None it is mean that order didn't create
            self.failed = False
        except Exception as e:
            self.failed = True
            print(f'Failed to create order with {self.exchange.id} {type(e).__name__} {str(e)}')
        # await self.exchange.close()
        self.response = response

    async def get_current_position(self):
        print('here')
        orders = await self.exchange.fetch_orders()
        self.current_order = orders[-1]
        await self.get_balance()
        # self.symbol
        # try:
        #     print(order[-1])
        # except:
        #     print('no orders')

    @staticmethod
    def check_if_already_exist(clients, new_client):
        for client in clients:
            if client.secret == new_client['secret'] and client.apiKey == new_client['apiKey']:
                return False
        return True
