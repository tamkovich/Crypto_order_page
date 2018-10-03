# -*- coding: utf-8 -*-

import os
import sys
import time

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt  # noqa: E402
import json

with open('config_test.json') as f:
    config = json.load(f)

exchange = ccxt.bitmex({
    'urls': {
            'api': 'https://testnet.bitmex.com'
        },
    'apiKey': config['bitmex'][0]['apiKey'],
    'secret': config['bitmex'][0]['secret'],
    'enableRateLimit': True,
})

symbol = 'BTC/USD'  # bitcoin contract according to https://github.com/ccxt/ccxt/wiki/Manual#symbols-and-market-ids
type = 'Market'  # or 'Market', or 'Stop' or 'StopLimit'
side = 'sell'  # or 'buy'
amount = 1.0
price = 6570.0  # or None

# extra params and overrides
params = {
    'stopPx': 6000.0,  # if needed
}

order = exchange.create_order(symbol, type, side, amount)
print(order)
# time.sleep(200)
# order = exchange.cancel_order(order['info']['orderID'])
# print(order)
