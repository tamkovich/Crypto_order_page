from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, String
from sqlalchemy import Column

Base = declarative_base()


class ClientBase(Base):

    __tablename__ = 'Client'

    id = Column(Integer, primary_key=True, autoincrement=True)
    apiKey = Column('apiKey', String(100), unique=True)
    secret = Column('secret', String(100), unique=True)

    def __init__(self, apiKey, secret):
        self.apiKey = apiKey
        self.secret = secret
