from flask import (
    Flask, render_template, redirect,
    flash, request, url_for, session,
    jsonify
)
from Order import Client
import asyncio
import json


app = Flask(__name__)
clients = []


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/create-order/', methods=['GET', 'POST'])
def login():
    error = ''
    try:
        data = {}
        if request.method == 'GET':
            side = request.args['side']

            tasks = [ioloop.create_task(c.create_market_order(side=side)) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            ioloop.run_until_complete(wait_tasks)
            for c in clients:
                data[c.exchange.id] = c.response
            ioloop.close()

        return jsonify(data)
    except Exception as e:
        # raise e
        pass


if __name__ == '__main__':
    app.config['SECRET_KEY'] = '123456'
    with open('config_test.json') as f:
        config = json.load(f)
    ioloop = asyncio.get_event_loop()
    for acc in config['bitmex']:
        client = Client(
            acc['apiKey'],
            acc['secret'],
        )
        clients.append(client)
    app.run()
