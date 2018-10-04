from flask import (
    Flask, render_template,
    request, jsonify
)
from Order import Client
from db import ClientTable, PythonSQL
import asyncio


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
        # ioloop.close()

        return jsonify(data)
    except Exception as e:
        raise e
        pass


if __name__ == '__main__':
    app.config['SECRET_KEY'] = '123456'
    db = PythonSQL('sqlite:///db.sqlite')
    config = db.select_all(ClientTable)
    db.close_session()
    ioloop = asyncio.get_event_loop()
    for acc in config:
        client = Client(
            acc[1],  # apiKey
            acc[2],  # secret
        )
        clients.append(client)
    app.run()
