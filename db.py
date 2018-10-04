from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import select
from sqlalchemy import Integer, String
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
meta = MetaData()
ClientTable = Table(
    'Client', meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('apiKey', String, unique=True),
    Column('secret', String, unique=True)
)


class PythonSQL:

    def __init__(self, db_name):
        self.engine = create_engine(
            db_name,
            # echo=True
        )
        self.conn = self.engine.connect()

        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def close_session(self):
        self.session.close()

    def insert(self, table, params):
        self.conn.execute(table.insert(), params)

    def select_all(self, table):
        select_st = select([table])
        res = self.conn.execute(select_st)
        response = []
        for _row in res:
            response.append(_row)
        return response


def main():
    db = PythonSQL('sqlite:///db.sqlite')
    print(db.select_all(ClientTable))
    db.close_session()


if __name__ == '__main__':
    main()
