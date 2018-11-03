from abc import ABC, abstractmethod

from app.models import ClientModel


class Table(ABC):

    table_data = dict()
    clients = None
    balance = 0

    def __init__(self):
        clients_objects = ClientModel.query.all()
        self.load_clients(clients_objects)

    @abstractmethod
    def add_client(self, key: str, secret: str):
        """
        create client object in DataBase and load it
        :param key: key to create object in DataBase
        :param secret: secret to create object in DataBase
        :return: None
        """
        pass

    @abstractmethod
    def add_order(self, **kwargs):
        """
        use ClientExample method create order
        :param kwargs: params to create order
        :return: None
        """
        pass

    @abstractmethod
    def add_failed_order(self, **kwargs):
        """
        use ClientExample to try open failed orders another time
        :param kwargs: params to create order
        :return: None
        """
        pass

    @abstractmethod
    def update_all(self):
        """
        update all clients data.
        use method update_orders()
        :return: None
        """
        pass

    @abstractmethod
    def view(self):
        """
        structure all orders and clients to dict()-view
        :return: None
        """
        pass

    @abstractmethod
    def _compose_failed(self):
        """
        generate data from failed orders
        :return: None
        """
        pass

    @abstractmethod
    def gen_data(self) -> dict:
        """
        Structure all data for the front-end part
        :return: <dict> front-end data
        """
        pass

    @abstractmethod
    def load_clients(self, clients_objects):
        """
        self.clients: <list>
        self.clients = [ClientExample(client_object) for client_object in clients_objects]
        :param clients_objects: list of client objects from DataBase
        :return: None
        """
        pass

    @abstractmethod
    def close_all_orders(self):
        """
        use func rm_all_orders() in ExampleApiExchange to delete all open orders
        :return: None
        """
        pass
