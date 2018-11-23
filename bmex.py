import ccxt.async_support as ccxt
import asyncio

round_ = lambda x: round(float(x) * 2) / 2


class BmexClient:

    retry = 3
    debug_mode = False
    debug_files_path = 'debug/'
    test_mode = True
    _symbol = {'BTC/USD': 'XBTUSD'}

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret
        self.symbol = 'BTC/USD'
        self.failed = False
        self.balance = {}
        self.order = {}
        self.exchange = None
        self.orders = dict()
        self.positions = dict()
        self.invalid_price = False

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
        balance = {}
        for _ in range(self.retry):
            try:
                balance = await self.exchange.fetch_balance()
                break
            except ccxt.AuthenticationError:
                break
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                await asyncio.sleep(0.5)
        try:
            self.balance["walletBalance"] = balance["info"][0]["walletBalance"]
            self.balance["marginBalance"] = balance["info"][0]["marginBalance"]
        except (TypeError, KeyError):
            self.balance = {}
        self._debug('get_balance', {'balance': balance, 'self': self.balance})
        await self.exchange.close()

    def _debug(self, filename, params={}):
        if self.debug_mode:
            with open(f'{self.debug_files_path}{filename}_{self.key}.txt', 'w') as f:
                for k in params.keys():
                    f.write(f'{k} = {params[k]}\n')

    async def _create_order(self, order_type, side, amount, price=None, params={}):
        self.invalid_price = False

        order = {}
        price = round_(price) if price else None
        self.failed = True
        for _ in range(self.retry):
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
                break
            except ccxt.AuthenticationError as _er:
                break
            except ccxt.RequestTimeout as _ex:
                await asyncio.sleep(0.5)
            except (ccxt.ExchangeNotAvailable, ccxt.ExchangeError) as _ex:
                break
            except Exception as _er:
                await asyncio.sleep(0.5)
        if self.failed:
            self.order = {
                'order_type': order_type,
                'side': side,
                'amount': amount,
                'price': price,
                'params': params
            }
        else:
            self.order = order
            self._debug(f'create_{self.order.get("type")}_order', {'order': self.order})

    async def create_order(self, type, side, amount, price=None):
        self.load_exchange()
        # assert type in ['Stop', 'Market', 'Limit'], 'There is no such order-type. ' \
        #                                             'Valid order types: [Stop, Market, Limit]'
        if type == 'Market':
            await self._create_order(type, side, amount, price)
        else:
            if type == 'Stop':
                params = {"stopPx": round_(price), "execInst": "LastPrice"}
                await self._create_order(type, side, amount, None, params=params)
            else:
                await self._create_order(type, side, amount, price)

        if self.failed:
            self.order = {
                'order_type': type,
                'side': side,
                'amount': amount,
                'price': price,
            }
        await self.exchange.close()

    async def rm_all_orders(self):
        self.load_exchange()
        try:
            orders = await self.exchange.fetch_open_orders(self.symbol)
        except ccxt.AuthenticationError:
            orders = []
        if orders:
            for order in orders:
                await self._close_order(order['id'])
        else:
            self.order = {}
        self._debug('rm_all_orders', {'order': self.order, 'orders': orders})
        await self.exchange.close()

    async def rm_all_positions(self):
        self.load_exchange()
        try:
            response = await self.exchange.privatePostOrderClosePosition({'symbol': self._symbol[self.symbol]})
        except ccxt.AuthenticationError:
            response = None
        self._debug('rm_all_positions', {'response': response})
        await self.exchange.close()

    async def check_everything(self, orders_ids: list):
        self.load_exchange()
        for order_id in orders_ids:
            self.orders[order_id] = dict()
        orders = []
        positions = []
        for _ in range(self.retry):
            try:
                orders = await self.exchange.fetch_open_orders(self.symbol)
                break
            except ccxt.OrderNotFound:
                await asyncio.sleep(0.5)
            except ccxt.AuthenticationError:
                break
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                await asyncio.sleep(0.5)
            except Exception as _ex:
                await asyncio.sleep(0.5)
        for _ in range(self.retry):
            try:
                positions = await self.exchange.private_get_position(self.symbol)
                break
            except ccxt.OrderNotFound:
                await asyncio.sleep(0.5)
            except ccxt.AuthenticationError:
                break
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                await asyncio.sleep(0.5)
            except Exception as _ex:
                await asyncio.sleep(0.5)
        self.positions = list(filter(lambda p: p['isOpen'], positions))
        for position in self.positions:
            position['price'] = position['avgEntryPrice']
            position['amount'] = position['currentQty']
            position['side'] = 'sell' if position['amount'] < 0 else 'buy'

        self._debug('check_everything', {'positions': self.positions, '_pst': positions, 'orders': orders})
        for order in orders:
            if order['id'] in orders_ids:
                if not order.get('price'):
                    order['price'] = order['info']['stopPx']
                self.orders[order['id']] = order
        await self.exchange.close()

    async def _close_order(self, order_id: str):
        order = {}
        try:
            order = await self.exchange.cancel_order(order_id, self.symbol)
        except ccxt.AuthenticationError:
            pass
        self.order = {}
        self._debug('_close_order', {'order': self.order, 'response': order})

    async def current_price(self, type, side, amount, price=None):
        self.load_exchange()
        if type != 'Market':
            current_price = None
            try:
                markets = await self.exchange.fetchMarkets()
                for market in markets:
                    if market['symbol'] == self.symbol:
                        current_price = market['info']['askPrice']
                        break
            except ccxt.AuthenticationError:
                await asyncio.sleep(1)
            if (type == 'Stop' and side == 'sell') or (type == 'Limit' and side == 'buy'):
                self.invalid_price = int(price) > current_price
            elif (type == 'Stop' and side == 'buy') or (type == 'Limit' and side == 'sell'):
                self.invalid_price = int(price) < current_price
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
