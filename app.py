from gevent import monkey
from flask import (
    Flask, render_template,
    request
)
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
from forms import ClientForm
from Order import Client

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

    # method to add new client
    def __init__(self, apiKey, secret):
        self.apiKey = apiKey
        self.secret = secret


clients = []
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


def reload_data(do_async=True):
    count = len(clients)
    data = {}
    if do_async:
        tasks = [ioloop.create_task(c.get_balance()) for c in clients]
        wait_tasks = asyncio.wait(tasks)
        ioloop.run_until_complete(wait_tasks)
    for i in range(count):
        data[i] = {}
        data[i]['apiKey'] = clients[i].apiKey
        data[i]['balance'] = clients[i].balance if clients[i].balance else 0
        data[i]['order'] = clients[i].side
    return data, count


def background_data():
    while True:
        socketio.sleep(30)
        print('**run table**')
        data, count = reload_data()
        print(data)
        socketio.emit('my pos', {'data': data, 'count': count})
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
    side = data['side']
    tasks = [ioloop.create_task(c.create_market_order(side=side)) for c in clients]
    tasks.extend([ioloop.create_task(c.get_balance()) for c in clients])
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    data, count = reload_data(do_async=False)
    socketio.emit('my pos', {'data': data, 'count': count})
    # ioloop.close()


@socketio.on('add-client')
def add_client(data):
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
            data, count = reload_data()
            socketio.emit('my pos', {'data': data, 'count': count})
            print({'status': 'ok!'})
            return
        print({'status': 'already exists!'})
        return
    print({'status': 'fail!'})
    return


if __name__ == '__main__':
    app.config['SECRET_KEY'] = '123123abc'
    res = ClientModel.query.all()

    ioloop = asyncio.get_event_loop()
    for acc in res:
        client = Client(
            acc.apiKey,  # apiKey
            acc.secret,  # secret
        )
        clients.append(client)
    socketio.run(
        app,
        '127.0.0.1',
        5000,
        # debug=True
    )
