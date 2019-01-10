from data_ import BitmexDataHandler
from app.models import ClientModel
from private.redis_conn import r

import time


class BitmexWsStartingPoint:

    endpoint = "wss://testnet.bitmex.com/realtime"  # testnet
    symbols = ["XBTUSD"]

    def __init__(self, auth_subs, common_subs):
        self.auth_subs = auth_subs
        self.common_subs = common_subs
        self.clients = ClientModel.query.filter_by(visible=True).filter(ClientModel.email != 'autherror@email').all()

        self._preparing()
        self.common_wst = []
        self.wst = {}
        self._common_data()
        self._client_data()

        self.tracking()

    def tracking(self):
        while True:
            unvisible_client_id = r.get('unvisible_client_id')
            if unvisible_client_id is not None and eval(unvisible_client_id) != 0:
                client = ClientModel.query.get(eval(unvisible_client_id))
                r.set('unvisible_client_id', 0)
                for ws_key in self.wst:
                    if ws_key.apiKey == client.apiKey:
                        for s in self.wst[ws_key].symbol_list:
                            self.wst[ws_key].wst[s].exited = True
                            self.wst[ws_key].wst[s].exit()
                if client:
                    self.wst[client] = self._client_connect(client)
            client_id = r.get('client_id')
            if client_id is not None and eval(client_id) != 0:
                client = ClientModel.query.get(eval(client_id))
                r.set('client_id', 0)
                if client:
                    self.wst[client] = self._client_connect(client)
            time.sleep(5)

    def _common_data(self):
        self.common_wst = [
            BitmexDataHandler(
                None,
                self.symbols,
                self.endpoint,
                self.common_subs,
            )
        ]

    def _client_data(self):
        for client in self.clients:
            self.wst[client] = self._client_connect(client)

    @staticmethod
    def _preparing():
        r.set('client_id', 0)

    def _client_connect(self, client):
        return BitmexDataHandler(
            None,
            self.symbols,
            self.endpoint,
            self.auth_subs,
            api=client.apiKey,
            secret=client.secret
        )


def main():
    auth_subs = ["margin", "order", "position"]
    common_subs = ["quote"]
    BitmexWsStartingPoint(auth_subs, common_subs)


if __name__ == '__main__':
    main()
