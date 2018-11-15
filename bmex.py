import ccxt.async_support as ccxt
import asyncio

round_ = lambda x: round(float(x) * 2) / 2


class BmexClient:

    retry = 3
    debug_mode = False
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
                break
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                await asyncio.sleep(0.5)
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
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                await asyncio.sleep(0.5)
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
        assert type in ['Stop', 'Market', 'Limit'], 'There is no such order-type. ' \
                                                    'Valid order types: [Stop, Market, Limit]'
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
                break
            except ccxt.OrderNotFound:
                await asyncio.sleep(0.5)
            except ccxt.AuthenticationError:
                break
            except (ccxt.RequestTimeout, ccxt.ExchangeError) as _ex:
                await asyncio.sleep(0.5)
            except Exception as _ex:
                await asyncio.sleep(0.5)
        for order in orders:
            if order['id'] in orders_ids:
                if not order.get('price'):
                    order['price'] = order['info']['stopPx']
                self.orders[order['id']] = order
        # assert len(self.orders) == len(orders_ids), 'Length of orders you have not the same as in exchange'
        await self.exchange.close()

    async def _close_order(self, order_id: str):
        order = {}
        try:
            order = await self.exchange.cancel_order(order_id, self.symbol)
        except ccxt.AuthenticationError:
            pass
        self.order = {}
        self._debug('_close_order', {'order': self.order, 'response': order})


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
