import asyncio
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt.async_support as ccxt  # noqa: E402


async def test(exchange):
    print(await exchange.fetch_balance())

b1 = ccxt.bitmex({
      "apiKey": "28iB73C3uvYOOdY2IPTJvUMX",
      "secret": "HvhcA95w9bgdpeWeLIn3mG68dRaVZ1d8O7y6jQygPFEstlUD",
      'timeout': 30000,
      'enableRateLimit': True,
      "verbose": True
})
b2 = ccxt.bitmex({
    "apiKey": "lSRRCw1cywzTMdtYwOjizK4v",
    "secret": "35u1f-nQ44q3MFOKIE2kfS_enidgDJ75Q7QqXrfeCfCfZKZp",
    'timeout': 30000,
    'enableRateLimit': True,
    'verbose': True,  # switch it to False if you don't want the HTTP log
})
b1.urls['api'] = b1.urls['test']  # ←----- switch the base URL to testnet
b2.urls['api'] = b2.urls['test']  # ←----- switch the base URL to testnet

[asyncio.ensure_future(test(exchange)) for exchange in [b1, b2]]
pending = asyncio.Task.all_tasks()
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(*pending))
