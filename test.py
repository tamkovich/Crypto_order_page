from Order import Client
import asyncio
import json


def read_config():
    with open('private/config_test.json', 'r') as f:
        return json.load(f)


def push_config(res):
    with open('private/config_test.json', 'w') as f:
        json.dump(res, f)


def test_create_market_order():
    res = read_config()
    clients = []
    for acc in res['bitmex']:
        clients.append(Client(acc['apiKey'], acc['secret']))
    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(c.create_market_order('sell', 200)) for c in clients]
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    ioloop.close()
    for i in range(len(res)):
        print(clients[i].order)
        res['bitmex'][i]['order'] = clients[i].order

    push_config(res)


def test_auth():
    c = Client('key', 'secret', order_id=4, order_exist=True)
    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(c.check_order())]
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    ioloop.close()
    print('And still')
    print(c.auth)


def test_check_for_blank_in_json_by_fields(data, *args):
    print(args)
    print(data)


if __name__ == '__main__':
    test_check_for_blank_in_json_by_fields({'side': 'buy', 'amount': 1, 'price': 1}, 'amount', 'price')

