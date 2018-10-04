import ccxt.async_support as ccxt


class Client:

    def __init__(self, apiKey, secret, test_mode=True):
        self.apiKey = apiKey
        self.secret = secret
        self.test_mode = test_mode
        self.symbol = 'BTC/USD'  # change for your symbol
        self.response = None
        self.balance = None
        self.side = None  # 'sell' or 'buy'

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
        self.side = side
        try:
            # Market
            response = await self.exchange.create_order(self.symbol, 'Market', side, amount)
        except Exception as e:
            print(f'Failed to create order with {self.exchange.id} {type(e).__name__} {str(e)}')
        # await self.exchange.close()
        self.response = response
