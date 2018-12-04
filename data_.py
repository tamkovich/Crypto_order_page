from base.data import DataHandler
from base.event import MarketEvent
from ws_common import BitMEXWebsocket

import websocket
import threading
import traceback
import json
import logging
import urllib
from typing import List

from util_.ws_util import *

NAMESPACE = "ws_tickmex"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename=f"{NAMESPACE}.log",
)
logger = logging.getLogger(__name__)


class BitmexDataHandler(DataHandler):
    ###
    def get_latest_bars(self, symbol, N=1):
        pass
        # todo: ccxt fetcher

    def get_latest_bar_datetime(self, symbol):
        pass
        # todo: ccxt fetcher

    def get_latest_bars_values(self, symbol, val_type, N=1):
        pass
        # todo: ccxt fetcher

    def update_bars(self):
        pass
        # todo: ws bar subscribe

    def get_latest_tickers(self, symbol, N=1):
        return self.latest_symbol_data[symbol]

    def get_latest_ticker_datetime(self, symbol):
        pass

    def update_tickers(self, symbol, ticker):
        last = self.latest_symbol_data[symbol]
        if ticker.get("bid") == last.get("bid") and ticker.get("ask") == last.get(
            "ask"
        ):
            return

        self.latest_symbol_data[symbol] = ticker
        self.events.put(MarketEvent())
        logger.debug(f"{symbol}, {ticker}")

    def create_fill(self, order):
        pass

    ###
    def __init__(self, events, symbol_list, endpoint, subs, api=None, secret=None):
        self.events = events
        self.symbol_list = symbol_list
        self.endpoint = endpoint
        self.api = api
        self.secret = secret

        self.symbol_data = {}
        self.latest_symbol_data = dict.fromkeys(self.symbol_list, {})
        self.bar_index = 0
        self.wst = {}
        self.subs = subs

        self._make_register()

    def callback(self, symbol, data, table):
        if table == "order":
            order = data[-1]
            print(order)
        if table == "quote":
            last_quote = data[-1]
            d = {"bid": last_quote["bidPrice"], "ask": last_quote["askPrice"]}
            self.update_tickers(symbol, d)

    def ws_common_callback(self, ch, method, properties, body):
        if method.routing_key == "quote":
            body = json.loads(body)
            d = {"bid": body["bidPrice"], "ask": body["askPrice"]}
            self.update_tickers(body["symbol"], d)
        if method.routing_key == "quoteBin5m":
            logger.debug(json.loads(body))

    def _make_register(self):
        # Common
        # common_subs = list(set(self.subs).intersection(NO_AUTH))
        # if common_subs:
        #     for s in self.symbol_list:
        #         r = Rabbit(s)
        #         self.latest_symbol_data[s] = {}
        #         thr = threading.Thread(
        #             target=lambda: r.start_consume_draft(
        #                 common_subs, self.ws_common_callback
        #             )
        #         )
        #         thr.daemon = True
        #         thr.start()

        # order ws
        auth_subs = list(set(self.subs).intersection(AUTH))
        if auth_subs:
            for s in self.symbol_list:
                self.wst[s] = BitMEXWebsocket(
                    self.endpoint,
                    s,
                    self.api,
                    self.secret,
                )
