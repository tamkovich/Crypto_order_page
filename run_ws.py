from data_ import BitmexDataHandler
from app.models import ClientModel
from private.redis_conn import r

import time


endpoint = "wss://testnet.bitmex.com/realtime"
symbols = ["XBTUSD"]
auth_subs = ["margin", "order", "position"]
no_auth_subs = ["quote"]


def client_ws(client):
    return BitmexDataHandler(
        None,
        symbols,
        endpoint,
        auth_subs,
        api=client.apiKey,
        secret=client.secret
    )


def main():
    clients = ClientModel.query.filter_by(visible=True).filter(ClientModel.email != 'autherror@email').all()
    # clients = []
    r.set('client_id', 0)
    # common
    common_wst = [
        BitmexDataHandler(
            None,
            symbols,
            endpoint,
            no_auth_subs,
        )
    ]
    # auth
    wst = {}
    for client in clients:
        wst[client] = client_ws(client)

    while True:
        unvisible_client_id = r.get('unvisible_client_id')
        if unvisible_client_id is not None and eval(unvisible_client_id) != 0:
            client = ClientModel.query.get(eval(unvisible_client_id))
            r.set('unvisible_client_id', 0)
            for ws_key in wst:
                if ws_key.apiKey == client.apiKey:
                    for s in wst[ws_key].symbol_list:
                        wst[ws_key].wst[s].exited = True
                        wst[ws_key].wst[s].exit()
            if client:
                wst[client] = client_ws(client)
        client_id = r.get('client_id')
        if client_id is not None and eval(client_id) != 0:
            client = ClientModel.query.get(eval(client_id))
            r.set('client_id', 0)
            if client:
                wst[client] = client_ws(client)
        time.sleep(5)


if __name__ == '__main__':
    main()
