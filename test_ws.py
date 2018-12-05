from data_ import BitmexDataHandler
from app.models import ClientModel
from private.redis_conn import r

import logging
import time

NAMESPACE = "run_ws"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename=f'{NAMESPACE}.log')
logger = logging.getLogger(__name__)

endpoint = "wss://testnet.bitmex.com/realtime"
symbols = ["XBTUSD"]
subs = ["margin"]


def client_ws(client):
    return BitmexDataHandler(None, symbols, endpoint, subs, api=client.apiKey, secret=client.secret)


def main():
    clients = ClientModel.query.filter_by(visible=True).filter(ClientModel.email != 'autherror@email').all()
    wst = {}
    for client in clients:
        wst[client] = client_ws(client)
    while True:
        client_id = r.get('client_id')
        if client_id is not None and eval(client_id) != 0:
            client = ClientModel.query.get(eval(client_id))
            r.set('client_id', 0)
            if client:
                wst[client] = client_ws(client)
        time.sleep(5)


if __name__ == '__main__':
    main()
