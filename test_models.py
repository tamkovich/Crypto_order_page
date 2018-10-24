from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, String
from sqlalchemy import Column

Base = declarative_base()


class ClientBase(Base):

    __tablename__ = 'Client'

    id = Column(Integer, primary_key=True, autoincrement=True)
    apiKey = Column('apiKey', String(100), unique=True)
    secret = Column('secret', String(100), unique=True)
    balance = Column('balance', Integer)
    order_type = Column('order_type', String(15))
    symbol = Column('symbol', String(10))
    contracts = Column('contracts', Integer)
    open = Column('open', Integer)
    side = Column('side', String(10))
    liquidation = Column('liquidation')

    def __init__(self, apiKey, secret, balance, order_type,
                 symbol, contracts, open, side):
        self.apiKey = apiKey
        self.secret = secret
        self.balance = balance
        self.order_type = order_type
        self.symbol = symbol
        self.contracts = contracts
        self.open = open
        self.side = side
