from gevent import monkey
from flask import (
    Flask, render_template,
    request
)
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
from forms import ClientForm
from Order import Client, update_client_data

import asyncio

monkey.patch_all()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
db = SQLAlchemy(app)


class ClientModel(db.Model):

    __tablename__ = 'Client'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    apiKey = db.Column(db.String(100), unique=True)
    secret = db.Column(db.String(100), unique=True)
    balance = db.Column('balance', db.Integer)
    order_type = db.Column('order_type', db.String(15))
    symbol = db.Column('symbol', db.String(10))
    contracts = db.Column('contracts', db.Integer)
    open = db.Column('open', db.Integer)
    side = db.Column('side', db.String(10))
    liquidation = db.Column('liquidation')
    failed = db.Column('failed', db.Boolean, default=False)
    current_order_exist = db.Column('current_order_exist', db.Boolean, default=False)
    current_order_id = db.Column('current_order_id', db.Integer)

    # method to add new client
    def __init__(self, apiKey, secret, balance=0, order_type='null', symbol='BTC/USD',
                 contracts=0, open=0, side=0, liquidation=0, failed=False,
                 current_order_exist=False, current_order_id=0):
        self.apiKey = apiKey
        self.secret = secret
        self.balance = balance
        self.order_type = order_type
        self.symbol = symbol
        self.contracts = contracts
        self.open = open
        self.side = side
        self.liquidation = liquidation
        self.failed = failed
        self.current_order_exist = current_order_exist
        self.current_order_id = current_order_id


# clients = []
socketio = SocketIO(app, async_mode=None)
thread_lock = Lock()
thread = None


# @app.before_first_request
# def rm_test_user():
#     c = ClientModel.query.all()[-1]
#     db.session.delete(c)
#     db.session.commit()


@app.route('/')
def hello_world():
    form = ClientForm(request.form)
    return render_template('index.html', async_mode=socketio.async_mode, form=form)


def reload_data():
    clients_db = ClientModel.query.all()
    clients = []
    for c in clients_db:
        clients.append(Client(c.apiKey, c.secret))
    count = len(clients)
    data = {}
    while True:
        try:
            tasks = [reload_loop.create_task(c.gen_data()) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            reload_loop.run_until_complete(wait_tasks)
            break
        except:
            print('[gen-data only] sleep for 3 seconds')
            socketio.sleep(3)
    for i in range(count):
        data[i] = {}
        data[i]['data'] = update_client_data(clients_db[i], clients[i].get_table_data())
    return data, count


def background_data():
    while True:
        socketio.sleep(30)
        print('**run table**')
        data, count = reload_data()
        print(data)
        socketio.emit('reload-table', {'data': data, 'count': count})
        socketio.sleep(30)


@socketio.on('connect')
def test_connect():
    print('connected')
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_data)
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('my event')
def handle_event(data):
    print('received json: ' + str(data))
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('create-order')
def create_order(data):
    clients = []
    clients_db = ClientModel.query.all()
    for c in clients_db:
        clients.append(Client(c.apiKey, c.secret))
    side = data['side']
    while True:
        try:
            tasks = [reload_loop.create_task(c.create_market_order(side=side)) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            reload_loop.run_until_complete(wait_tasks)
            break
        except:
            print('[create-order] sleep for 3 seconds')
            socketio.sleep(3)
    data = {}
    count = len(clients)
    for i in range(count):
        data[i] = {}
        data[i]['data'] = update_client_data(clients_db[i], clients[i].get_table_data())
    socketio.emit('reload-table', {'data': data, 'count': count})


@socketio.on('close-order')
def close_order():
    clients = []
    clients_db = ClientModel.query.all()
    for c in clients_db:
        clients.append(Client(c.apiKey, c.secret))
    while True:
        try:
            tasks = [reload_loop.create_task(c.close_order(order_id=c.current_order_id)) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            reload_loop.run_until_complete(wait_tasks)
            break
        except:
            print('[close-order] sleep for 3 seconds')
            socketio.sleep(3)
    data = {}
    count = len(clients)
    for i in range(count):
        data[i] = {}
        data[i]['data'] = update_client_data(clients_db[i], clients[i].get_table_data())
    socketio.emit('reload-table', {'data': data, 'count': count})


@socketio.on('add-client')
def add_client(data):
    clients = []
    for c in ClientModel.query.all():
        clients.append(Client(c.apiKey, c.secret))
    apiKey, secret = data['form'].split('&')
    apiKey = apiKey.split('=')[-1]
    secret = secret.split('=')[-1]
    form = ClientForm(apiKey=apiKey, secret=secret)
    if form.validate():
        if Client.check_if_already_exist(clients, {'apiKey': form.apiKey.data, 'secret': form.secret.data}):
            client = Client(
                form.apiKey.data,
                form.secret.data
            )
            # clients.insert(0, client)  # add to front
            clients.append(client)  # add to back
            db.session.add(ClientModel(client.apiKey, client.secret))
            db.session.commit()

            count = len(clients)
            data = {}
            while True:
                try:
                    tasks = [reload_loop.create_task(c.gen_data()) for c in clients]
                    wait_tasks = asyncio.wait(tasks)
                    reload_loop.run_until_complete(wait_tasks)
                    break
                except:
                    print('[add-client] sleep for 3 seconds')
                    socketio.sleep(3)

            clients_db = ClientModel.query.all()
            for i in range(count):
                data[i] = {}
                data[i]['data'] = update_client_data(clients_db[i], clients[i].get_table_data())
            socketio.emit('reload-table', {'data': data, 'count': count})
            print({'status': 'ok!'})
            return
        print({'status': 'already exists!'})
        return
    print({'status': 'fail!'})
    return


if __name__ == '__main__':
    app.config['SECRET_KEY'] = '123123abc'
    reload_loop = asyncio.get_event_loop()
    socketio.run(
        app,
        '127.0.0.1',
        5000,
        # debug=True
    )
