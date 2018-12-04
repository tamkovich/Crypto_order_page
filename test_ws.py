from data_ import BitmexDataHandler
from app.models import ClientModel

import logging
import redis
import time

NAMESPACE = "ws_tickmex"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename=f'{NAMESPACE}.log')
logger = logging.getLogger(__name__)

r = redis.StrictRedis(host='localhost',charset="utf-8", port=6379, db=0)


def main():
    clients = ClientModel.query.filter_by(visible=True).filter(ClientModel.email != 'autherror@email').all()
    endpoint = "wss://testnet.bitmex.com/realtime"
    symbols = ["XBTUSD"]
    subs = ["wallet"]
    wst = {}
    for client in clients:
        wst[client] = BitmexDataHandler(None, symbols, endpoint, subs, api=client.apiKey, secret=client.secret)
    while True:
        # print(r.keys())
        # print(r.get("abcdefg"))
        time.sleep(5)


if __name__ == '__main__':
    main()
