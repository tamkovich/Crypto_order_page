from private.redis_conn import r


class WsDataHandler:

    def __init__(self, key, logger=None):
        self.r = r
        self.key = key
        self.logger = logger

    def man(self, message, table, *args, **kwargs):
        process = getattr(self, f'_{type(self).__name__}__save_{table}')
        process(message=message, key=self.key, *args, **kwargs)

    #
    # End Public Methods
    #

    @staticmethod
    def __save_quote(*args, **kwargs):
        __table_name__ = 'quote'
        message = kwargs['message']

        last_quote = message["data"][-1]
        d = {
            "bid": last_quote["bidPrice"],
            "ask": last_quote["askPrice"],
            "ts": last_quote["timestamp"],
        }
        r.set(f"{__table_name__}:{last_quote['symbol']}", str(d))

    @staticmethod
    def __save_margin(*args, **kwargs):
        __table_name__ = 'margin'
        message = kwargs['message']
        key = kwargs['key']

        for mess in message["data"]:
            if mess.get("walletBalance") is not None:
                r.set(f"{__table_name__}:{key}:walletBalance", mess["walletBalance"] / 100000000)
            if mess.get("marginBalance") is not None:
                r.set(f"{__table_name__}:{key}:marginBalance", mess["marginBalance"] / 100000000)
            if mess.get("marginLeverage") is not None:
                r.set(f"{__table_name__}:{key}:marginLeverage", mess["marginLeverage"])

    @staticmethod
    def __save_order(*args, **kwargs):
        __table_name__ = 'order'
        message = kwargs['message']
        key = kwargs['key']

        for mess in message["data"]:
            order = r.get(f"{__table_name__}:{key}:{mess['orderID']}")
            order = eval(order) if order else {}
            for field in mess:
                order[field] = mess[field]
            r.set(f"{__table_name__}:{key}:{mess['orderID']}", str(order))

    @staticmethod
    def __save_position(*args, **kwargs):
        __table_name__ = 'position'
        message = kwargs['message']
        key = kwargs['key']

        for mess in message["data"]:
            position = r.get(f"{__table_name__}:{key}")
            position = eval(position) if position else {}
            for field in mess:
                position[field] = mess[field]
            r.set(f"{__table_name__}:{key}", str(position))
