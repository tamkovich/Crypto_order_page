from abc import ABC, abstractmethod


class Order(ABC):

    # order & position
    symbol = None
    type = None
    side = None
    price = None
    amount = None

    # position only
    liquidation = None
    leverage = None

    def __init__(self, order_object):
        try:
            self.id = order_object.order_exchange_id
        except:
            self.id = None

    @abstractmethod
    def update(self, **kwargs):
        """
        updates order data
        :return: None
        """
        pass


class Client(ABC):

    api = None
    balance = None
    orders = None
    positions = []

    def __init__(self, client_object):
        assert client_object, 'You have to create Client firstly'
        key = client_object.apiKey
        secret = client_object.secret
        self.client_object = client_object
        self.load_api(key, secret)
        orders_objects = client_object.orders
        self.load_orders(orders_objects)

    @abstractmethod
    def create_order(self):
        """
        Creates order
        :return: None
        """
        pass

    @abstractmethod
    def get_balance(self):
        """
        fetch balance from api-exchange
        :return: None
        """
        pass

    @abstractmethod
    def update_orders(self):
        """
        run from table-method update_all()
        update all orders data
        use order-method update()
        :return: None
        """
        pass

    # @abstractmethod
    # def update_positions(self):
    #     """
    #     run from table-method update_all()
    #     update all positions data
    #     use order-method update()
    #     :return: None
    #     """
    #     pass

    @abstractmethod
    def load_api(self, key: str, secret: str):
        """
        self.api = ExampleApi(key, secret)
        :param key: key of exchange
        :param secret: secret of exchange
        :return: None
        """
        pass

    @abstractmethod
    def load_orders(self, orders_objects):
        """
        self.orders = OrderExample(orders_objects)
        :param orders_objects: DataBase Client objects
        :return: None
        """
        pass
