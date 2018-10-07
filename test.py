import json
from Order import Client
import asyncio


def read_config():
    with open('private/config_test.json', 'r') as f:
        return json.load(f)


def push_config(res):
    with open('private/config_test.json', 'w') as f:
        json.dump(res, f)


if __name__ == '__main__':
    res = read_config()
    clients = []
    for acc in res['bitmex']:
        clients.append(Client(acc['apiKey'], acc['secret']))
    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(c.create_market_order('sell', 200)) for c in clients]
    # tasks = [ioloop.create_task(c.get_current_position()) for c in clients]
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    ioloop.close()
    for i in range(len(res)):
        print(clients[i].response)
        res['bitmex'][i]['current_order'] = clients[i].response

    push_config(res)

