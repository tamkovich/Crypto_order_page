# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import json
import time

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt.async_support as ccxt_async
import ccxt


async def test_real_async(apiKey, secret, test_mode=True):
    exchange = ccxt_async.bitmex({
        'apiKey': apiKey,
        'secret': secret,
        'timeout': 30000,
        'enableRateLimit': True,
    })

    response = None

    if test_mode:
        if 'test' in exchange.urls:
            exchange.urls['api'] = exchange.urls['test']  # ←----- switch the base URL to testnet

    exchange.verbose = True  # this is for debugging

    symbol = 'BTC/USD'  # change for your symbol
    ordType = 'Market'  # or 'Market', or 'Stop' or 'StopLimit'
    side = 'sell'       # or 'buy'
    amount = 1.0        # change the amount
    price = 6570.0      # change the price

    try:
        # Market
        response = await exchange.create_order(symbol, ordType, side, amount)
        # LimitBuy
        # response = await exchange.create_limit_buy_order(symbol, side, amount)

    except Exception as e:
        print('Failed to create order with', exchange.id, type(e).__name__, str(e))

    await exchange.close()
    return response


async def test(apiKey, secret, test_mode=True):
    exchange = ccxt.bitmex({
        'apiKey': apiKey,
        'secret': secret,
        'timeout': 30000,
        'enableRateLimit': True,
    })

    response = None

    if test_mode:
        if 'test' in exchange.urls:
            exchange.urls['api'] = exchange.urls['test']  # ←----- switch the base URL to testnet

    symbol = 'BTC/USD'  # change for your symbol
    ordType = 'Market'  # or 'Market', or 'Stop' or 'StopLimit'
    side = 'sell'       # or 'buy'
    amount = 1.0        # change the amount
    price = 6570.0      # change the price

    try:
        # Market
        response = exchange.create_order(symbol, ordType, side, amount)
        # LimitBuy
        # response = exchange.create_limit_buy_order(symbol, side, amount)

    except Exception as e:
        print(f'Failed to create order with {exchange.id} {type(e).__name__} {str(e)}')

    return response


if __name__ == '__main__':
    with open('config_test.json') as f:
        config = json.load(f)
    ioloop = asyncio.get_event_loop()
    for _ in range(3):
        tasks = [ioloop.create_task(test_real_async(acc['apiKey'], acc['secret'])) for acc in config['bitmex']]
        wait_tasks = asyncio.wait(tasks)
        print(ioloop.run_until_complete(wait_tasks))
        time.sleep(2)
    ioloop.close()
