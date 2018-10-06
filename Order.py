import ccxt.async_support as ccxt


class Client:

    def __init__(self, apiKey, secret, test_mode=True):
        self.apiKey = apiKey
        self.secret = secret
        self.test_mode = test_mode
        self.symbol = 'BTC/USD'  # change for your symbol
        self.response = None
        self.balance = None
        self.side = None         # 'sell' or 'buy'
        self.failed = False      # 'True' if order not created

        self.exchange = ccxt.bitmex({
            'apiKey': apiKey,
            'secret': secret,
            'timeout': 30000,
            'enableRateLimit': True,
        })

        if self.test_mode:
            if 'test' in self.exchange.urls:
                self.exchange.urls['api'] = self.exchange.urls['test']  # ←----- switch the base URL to testnet

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

    @staticmethod
    def check_if_already_exist(clients, new_client):
        for client in clients:
            if client.secret == new_client['secret'] and client.apiKey == new_client['apiKey']:
                return False
        return True
