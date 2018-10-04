from flask import (
    Flask, render_template,
    request, jsonify, session
)
from flask_socketio import SocketIO, emit, disconnect
from threading import Lock
from Order import Client
from db import ClientTable, PythonSQL
import asyncio


app = Flask(__name__)
clients = []
async_mode = None
socketio = SocketIO(app, async_mode=async_mode)
thread_lock = Lock()
thread = None


@app.route('/')
def hello_world():
    return render_template('index.html', async_mode=socketio.async_mode)


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


def background_data():
    count = len(clients)
    data = {}
    tasks = [ioloop.create_task(c.get_balance()) for c in clients]
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    for i in range(count):
        data[i] = {}
        data[i]['apiKey'] = clients[i].apiKey
        data[i]['balance'] = clients[i].balance
        data[i]['order'] = clients[i].side
    socketio.emit('my pos', {'data': data, 'count': count})


def handle_connect():
    global thread
    with thread_lock:
        # if thread is None:
        thread = socketio.start_background_task(target=background_data)


@socketio.on('my event')
def handle_event(data):
    print('received json: ' + str(data))
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('my table')
def handle_table():
    print('**run table**')
    handle_connect()


if __name__ == '__main__':
    app.config['SECRET_KEY'] = 'secret!'
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
    # app.run()
    socketio.run(app)
