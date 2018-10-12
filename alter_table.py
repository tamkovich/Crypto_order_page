from sqlalchemy import Integer, String, Boolean
from sqlalchemy import Column
from db import PythonSQL


def alter_table(table_name):
    cols = dict()
    cols['balance'] = Column('balance', Integer)
    cols['order_type'] = Column('order_type', String(15))
    cols['symbol'] = Column('symbol', String(10))
    cols['contracts'] = Column('contracts', Integer)
    cols['open'] = Column('open', Integer)
    cols['side'] = Column('side', String(10))
    cols['liquidation'] = Column('liquidation', Integer)
    cols['failed'] = Column('failed', Boolean, default=False)
    cols['current_order_exist'] = Column('current_order_exist', Boolean, default=False)
    cols['current_order_id'] = Column('current_order_id', Integer)

    # db = PythonSQL('sqlite:///db.sqlite')
    db = PythonSQL("postgresql://localhost/clients_db")
    for col in cols.keys():
        db.add_column(table_name, cols[col])


def main():
    alter_table(table_name='Client')


if __name__ == '__main__':
    main()
