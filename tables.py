from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import Integer, String

meta = MetaData()

ClientTable = Table(
    'client', meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('apiKey', String, unique=True),
    Column('secret', String, unique=True)
)

User = Table(
    'user', meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String),
    Column('password', String)
)

OrderTable = Table(
    'order', meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('username', String),
    Column('password', String)
)
