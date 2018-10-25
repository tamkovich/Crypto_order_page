from abc import ABC, abstractmethod


class Table(ABC):

    def __init__(self):
        self.clients = list()

    @abstractmethod
    def add_order(self):
        pass

    @abstractmethod
    def update_all(self):
        pass

    @abstractmethod
    def view(self):
        pass
