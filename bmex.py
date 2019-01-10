import ccxt.async_support as ccxt
import asyncio

from private.redis_conn import r
from loggers import get_logger

logger = get_logger('bmex')
round_ = lambda x: round(float(x) * 2) / 2


class BmexClient:

    retry = 3
    debug_mode = False
    debug_files_path = 'debug/'
    test_mode = True
    _symbol = {'BTC/USD': 'XBTUSD'}

    def __init__(self, key, secret, email):
        self.key = key
        self.secret = secret
        self.email = email
        self.symbol = 'BTC/USD'
        self.failed = False
        self.balance = {}
        self.order = {}
        self.exchange = None
        self.orders = dict()
        self.positions = dict()
        self.invalid_price = False

    ### INFO VIA ASYNCIO ###

    async def update_user_info(self):
        if self.email is None:
            self.__load_exchange()
            try:
                response = await self.exchange.privateGetUser()
                self.email = response['email']
                self._debug('update_user_info', {'response': response})
            except ccxt.AuthenticationError:
                self.email = 'autherror@email'
            await self.exchange.close()

    ### ACTIONS VIA ASYNCIO ###

    async def create_order(self, type, side, amount, price=None):
        logger.info(f'GET {type}|{side}|{amount}|{price}')
        if type == 'Market':
            await self._create_order(type, side, amount, price)
        else:
            if type == 'Stop':
                params = {"stopPx": round_(price), "execInst": "LastPrice"}
                await self._create_order(type, side, amount, None, params=params)
            else:
                await self._create_order(type, side, amount, price)
        logger.info(f'RETURN {self.order}')

    async def _create_order(self, order_type, side, amount, price=None, params={}):
        self.__load_exchange()
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
        await self.exchange.close()

    async def rm_all_orders(self):
        self.__load_exchange()
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
        self.__load_exchange()
        try:
            response = await self.exchange.privatePostOrderClosePosition({'symbol': self._symbol[self.symbol]})
        except ccxt.AuthenticationError:
            response = None
        self._debug('rm_all_positions', {'response': response})
        await self.exchange.close()

    async def _close_order(self, order_id: str):
        order = {}
        try:
            order = await self.exchange.cancel_order(order_id, self.symbol)
        except ccxt.AuthenticationError:
            pass
        self.order = {}
        self._debug('_close_order', {'order': self.order, 'response': order})

    ### INFO VIA REDIS ###

    def redis_get_balance(self):
        """Fetch walletBalance and marginBalance from Redis"""

        wb = r.get(f'margin:{self.key}:walletBalance')
        if wb:
            self.balance['walletBalance'] = eval(wb)
        mb = r.get(f'margin:{self.key}:marginBalance')
        if mb:
            self.balance['marginBalance'] = eval(mb)

    def redis_check_everything(self, orders_ids):
        """
        Updates every order and positions info. Note, that it updates only
        those orders which were created from the current service/application.
        """
        for order_id in orders_ids:
            self.orders[order_id] = dict()
        positions = r.get(f"position:{self.key}")
        positions = [eval(positions)] if positions else []
        self.positions = list(filter(lambda p: p['isOpen'], positions))
        for position in self.positions:
            position['price'] = position['avgEntryPrice']
            position['amount'] = position['currentQty']
            position['side'] = 'sell' if position['amount'] < 0 else 'buy'
            if position['crossMargin'] is True:
                position['leverage'] = r.get(f"margin:{self.key}:marginLeverage")
                position['leverage'] = eval(position['leverage']) if position['leverage'] else None
        orders_keys = r.keys(f'order:{self.key}:*')
        orders = list(map(lambda key: eval(r.get(key)), orders_keys))
        _to_delete = []
        for order in orders:
            if order['ordStatus'] in ['Filled', 'Canceled']:
                _to_delete.append(f'order:{self.key}:{order["orderID"]}')
                continue
            if order['orderID'] in orders_ids:
                if not order.get('price'):
                    order['price'] = order['stopPx']
                order['type'] = order['ordType']
                order['amount'] = order['orderQty']
                self.orders[order['orderID']] = order
        if _to_delete:
            r.delete(*_to_delete)

    def redis_current_price(self, type, side, amount, price=None):
        """
        Check current price via redis to check is `invalid_price`
        """
        self.invalid_price = False
        current_price = r.get(f"quote:{self._symbol[self.symbol]}")
        if current_price:
            current_price = eval(current_price)["ask"]
            if (type == 'Stop' and side == 'sell') or (type == 'Limit' and side == 'buy'):
                self.invalid_price = int(price) > current_price
            elif (type == 'Stop' and side == 'buy') or (type == 'Limit' and side == 'sell'):
                self.invalid_price = int(price) < current_price
        else:
            self.invalid_price = True

    #
    # End Public Methods
    #

    def _debug(self, filename, params={}):
        if self.debug_mode:
            with open(f'{self.debug_files_path}{filename}_{self.key}.txt', 'w') as f:
                for k in params.keys():
                    f.write(f'{k} = {params[k]}\n')

    def __load_exchange(self):
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
