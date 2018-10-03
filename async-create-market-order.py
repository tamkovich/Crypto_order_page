# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import json

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt.async_support as ccxt_async
import ccxt


async def test(apiKey, secret, test_mode=True):
    exchange = ccxt_async.bitmex({
        'apiKey': apiKey,
        'secret': secret,
        'enableRateLimit': True,
    })

    response = None

    if test_mode:
        if 'test' in exchange.urls:
            exchange.urls['api'] = exchange.urls['test']  # ←----- switch the base URL to testnet

    exchange.verbose = True  # this is for debugging

    symbol = 'BTC/USD'  # change for your symbol
    ordType = 'Market'  # or 'Market', or 'Stop' or 'StopLimit'
    side = 'sell'      # or 'buy'
    amount = 1.0       # change the amount
    price = 6570.0    # change the price

    try:
        # Market
        # response = await exchange.create_order(symbol, ordType, side, amount)
        # LimitBuy
        response = await exchange.create_limit_buy_order(symbol, side, amount)

    except Exception as e:
        print('Failed to create order with', exchange.id, type(e).__name__, str(e))

    await exchange.close()
    return response

if __name__ == '__main__':
    with open('config_test.json') as f:
        config = json.load(f)
    print(asyncio.get_event_loop().run_until_complete(
        test(
            config['bitmex'][0]['apiKey'],
            config['bitmex'][0]['secret']
        )
    ))
