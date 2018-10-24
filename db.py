from sqlalchemy import create_engine
from sqlalchemy import select, delete
from sqlalchemy.orm import sessionmaker
from tables import ClientTable, User, OrderTable

POSTGRES = {
    'user': 'user_name',
    'pw': 'password',
    'db': 'clients_db',
    'host': 'localhost',
    'port': '5432',
}


class PythonSQL:

    def __init__(self, db_name):
        self.db_name = db_name
        self.engine = create_engine(db_name)
        self.conn = self.engine.connect()
        self.session = sessionmaker(bind=self.engine)()

    def close_session(self):
        self.session.close()

    def insert(self, table, params):
        self.conn.execute(table.insert(), params)

    def select_all(self, table):
        select_st = select([table])
        response = [row for row in self.conn.execute(select_st)]
        return response

    def delete(self, table, params):
        delete([])

    def add_column(self, table_name, column):
        column_name = column.compile(dialect=self.engine.dialect)
        column_type = column.type.compile(self.engine.dialect)
        self.engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, column_name, column_type), extend_existing=True)


def main():
    db = PythonSQL('postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES)
    # print(db.engine.table_names())
    print(db.select_all(User))
    # config = db.select_all(ClientTable)
    # db.insert(User, {'username': 'trademan', 'password': 'wen234man'})
    # c = config[-1]
    # db.delete(ClientTable, c)
    # print(db.select_all(ClientTable))
    db.close_session()


if __name__ == '__main__':
    main()
