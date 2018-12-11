import websocket
import threading
import traceback
import json
import logging
import urllib
import time
import redis

from util_.ws_util import *

NAMESPACE = "ws_common"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename=f'{NAMESPACE}.log')
logger = logging.getLogger(__name__)

r = redis.StrictRedis(host='localhost', charset="utf-8", port=6379, db=0)


def find_by_keys(keys, rows, match):
    for r in rows:
        if all(r[k] == match[k] for k in keys):
            return r

# Naive implementation of connecting to BitMEX websocket for streaming realtime data.
# The Marketmaker still interacts with this as if it were a REST Endpoint, but now it can get
# much more realtime data without polling the hell out of the API.
#
# The Websocket offers a bunch of data as raw properties right on the object.
# On connect, it synchronously asks for a push of all this data then returns.
# Right after, the MM can start using its data. It will be updated in realtime, so the MM can
# poll really often if it wants.


class BitMEXWebsocket:

    # Don't grow a table larger than this amount. Helps cap memory usage.
    MAX_TABLE_LEN = 200

    def __init__(self, endpoint, symbol, subs, api_key=None, api_secret=None):
        """Connect to the websocket and initialize data stores."""
        self.logger = logging.getLogger(NAMESPACE)
        self.logger.debug("Initializing WebSocket.")

        self.endpoint = endpoint
        self.symbol = symbol
        self.subs = subs
        self.api_key = api_key
        self.api_secret = api_secret

        self.data = {}
        self.keys = {}
        self.exited = False

        # We can subscribe right in the connection querystring, so let's build that.
        # Subscribe to all pertinent endpoints
        wsURL = self.__get_url()
        self.logger.info("Connecting to %s" % wsURL)
        self.__connect(wsURL, symbol)
        print(f"{self.symbol} is loaded")
        self.logger.info("Connected to WS.")

        # Connected. Wait for partials
        # self.__wait_for_symbol(symbol)
        print(f"{self.symbol} is ok")
        self.logger.info("Got all market data. Starting.")

    def exit(self):
        """Call this to exit - will close websocket."""
        self.exited = True
        self.ws.close()

    def man(self, message, table):
        for mess in message["data"]:
            if table == 'margin':
                if mess.get("walletBalance"):
                    r.set(f"{table}:{self.api_key}:walletBalance", mess["walletBalance"] / 100000000)
                if mess.get("marginBalance"):
                    r.set(f"{table}:{self.api_key}:marginBalance", mess["marginBalance"] / 100000000)
                if mess.get("marginLeverage"):
                    r.set(f"{table}:{self.api_key}:marginLeverage", mess["marginLeverage"])
            elif table == 'order':
                print('ORDER:', mess)
                # r.set(f"{table}:{self.api_key}:", mess)
            elif table == 'position':
                position = r.get(f"{table}:{self.api_key}")
                position = eval(position) if position else {}
                for field in mess:
                    position[field] = mess[field]
                r.set(f"{table}:{self.api_key}", position)

    #
    # End Public Methods
    #

    def __get_auth(self):
        """Return auth headers. Will use API Keys if present in settings."""
        if self.api_key:
            self.logger.info("Authenticating with API Key.")
            # To auth to the WS using an API key, we generate a signature of a nonce and
            # the WS API endpoint.
            expires = generate_nonce()
            return [
                "api-expires: " + str(expires),
                "api-signature: "
                + generate_signature(self.api_secret, "GET", "/realtime", expires, ""),
                "api-key:" + self.api_key,
            ]
        else:
            self.logger.info("Not authenticating.")
            return []

    def _dirty_reconnect(self, ws):
        _sleeps = 3
        while True:
            try:
                ws.run_forever()
                _sleeps = 3
                time.sleep(_sleeps)
            except:
                _sleeps = 5
                time.sleep(_sleeps)

    def __connect(self, wsURL, symbol):
        """Connect to the websocket in a thread."""
        self.logger.debug("Starting thread")

        self.ws = websocket.WebSocketApp(
            wsURL,
            on_message=self.__on_message,
            on_close=self.__on_close,
            on_open=self.__on_open,
            on_error=self.__on_error,
            header=self.__get_auth(),
        )

        self.wst = threading.Thread(target=lambda: self._dirty_reconnect(self.ws))
        self.wst.daemon = True
        self.wst.start()
        self.logger.debug("Started thread")

        # Wait for connect before continuing
        conn_timeout = 5
        while not self.ws.sock or not self.ws.sock.connected and conn_timeout:
            time.sleep(1)
            conn_timeout -= 1
        if not conn_timeout:
            self.logger.error("Couldn't connect to WS! Exiting.")
            self.exit()
            raise websocket.WebSocketTimeoutException(
                "Couldn't connect to WS! Exiting."
            )

    def __get_url(self):
        """
        Generate a connection URL. We can define subscriptions right in the querystring.
        Most subscription topics are scoped by the symbol we're listening to.
        """

        # You can sub to orderBookL2 for all levels, or orderBook10 for top 10 levels & save bandwidth
        # subscriptions = [sub + ":" + self.symbol for sub in symbolSubs]

        urlParts = list(urllib.parse.urlparse(self.endpoint))
        urlParts[0] = urlParts[0].replace("http", "ws")
        urlParts[2] = "/realtime?subscribe={}".format(",".join(self.subs))
        return urllib.parse.urlunparse(urlParts)

    def __wait_for_symbol(self, symbol):
        """On subscribe, this data will come down. Wait for it."""
        while not {"instrument", "trade", "quote"} <= set(self.data):
            time.sleep(0.1)

    def __send_command(self, command, args=None):
        """Send a raw command."""
        if args is None:
            args = []
        self.ws.send(json.dumps({"op": command, "args": args}))

    def __on_message(self, ws, message):
        """Handler for parsing WS messages."""
        # timestamp = time.time()
        message = json.loads(message)
        self.logger.debug(json.dumps(message))

        table = message.get("table")
        action = message.get("action")
        try:
            if "subscribe" in message:
                self.logger.debug("Subscribed to %s." % message["subscribe"])
            elif action:
                if table not in self.data:
                    self.data[table] = []
                # There are four possible actions from the WS:
                # 'partial' - full table image
                # 'insert'  - new row
                # 'update'  - update row
                # 'delete'  - delete row
                # print(message['data'])
                if action == "partial":
                    self.logger.debug("%s: partial" % table)
                    self.data[table] += message["data"]
                    # Keys are communicated on partials to let you know how to uniquely identify
                    # an item. We use it for updates.
                    self.keys[table] = message["keys"]
                    self.man(message, table)
                elif action == "insert":
                    self.logger.debug("%s: inserting %s" % (table, message["data"]))
                    self.data[table] += message["data"]
                    # Limit the max length of the table to avoid excessive memory usage.
                    # Don't trim orders because we'll lose valuable state if we do.
                    if (
                            table not in ["orderBookL2"]
                            and len(self.data[table]) > BitMEXWebsocket.MAX_TABLE_LEN
                    ):
                        self.data[table] = self.data[table][
                                           int(BitMEXWebsocket.MAX_TABLE_LEN / 2):
                                           ]
                    self.man(message, table)
                elif action == "update":
                    self.logger.debug("%s: updating %s" % (table, message["data"]))
                    # Locate the item in the collection and update it.
                    for updateData in message["data"]:
                        item = find_by_keys(
                            self.keys[table], self.data[table], updateData
                        )
                        if not item:
                            return  # No item found to update. Could happen before push
                        item.update(updateData)
                        # Remove cancelled / filled orders
                        if table == "order" and item["leavesQty"] <= 0:
                            self.data[table].remove(item)
                    self.man(message, table)
                elif action == "delete":
                    self.logger.debug("%s: deleting %s" % (table, message["data"]))
                    # Locate the item in the collection and remove it.
                    for deleteData in message["data"]:
                        item = find_by_keys(
                            self.keys[table], self.data[table], deleteData
                        )
                        self.data[table].remove(item)
                    self.man(message, table)
                else:
                    raise Exception("Unknown action: %s" % action)
        except:
            self.logger.error(traceback.format_exc())

    def __on_error(self, ws, error):
        """Called on fatal websocket errors. We exit on these."""
        if not self.exited:
            self.logger.error("Error : %s" % error)
            raise websocket.WebSocketException(error)

    def __on_open(self, ws):
        """Called when the WS opens."""
        self.logger.debug("Websocket Opened.")

    def __on_close(self, ws):
        """Called on websocket close."""
        self.logger.info("Websocket Closed")

