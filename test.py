from BmexIhar.views import TableIhar

table = TableIhar()


def test_create_market_order():
    table.add_order(type='Market', side='Sell', amount=10)


def test_create_limit_order():
    table.add_order(type='Limit', side='Buy', amount=10, price=6200)


def test_create_stop_order():
    table.add_order(type='Stop', side='Sell', amount=10, price=4400)


def test_rm_all_orders():
    table.close_all_orders()


def test_add_client():
    key = ''
    secret = ''
    table.add_client(key, secret)


def test_update_table():
    table.update_all()
    table.view()
    print(table.table_data)


if __name__ == '__main__':
    test_create_stop_order()
    test_update_table()
