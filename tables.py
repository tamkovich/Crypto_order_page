from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import Integer, String

meta = MetaData()

ClientTable = Table(
    'Client', meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('apiKey', String, unique=True),
    Column('secret', String, unique=True)
)

User = Table(
    'UserClient', meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String),
    Column('password', String)
)
