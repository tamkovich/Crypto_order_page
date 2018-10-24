from gevent import monkey
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from threading import Lock
from forms import ClientForm, UserLoginForm
from Order import Client, update_client_data, check_for_blank_in_json_by_fields
from db import POSTGRES
from functools import wraps
import asyncio
import gc

monkey.patch_all()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'UserClient'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), unique=True)


# db.create_all()
# db.session.commit()


class ClientModel(db.Model):

    __tablename__ = 'Client'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    apiKey = db.Column(db.String(100), unique=True)
    secret = db.Column(db.String(100), unique=True)
    balance = db.Column('balance', db.Integer)
    order_type = db.Column('order_type', db.String(15))
    symbol = db.Column('symbol', db.String(10))
    amount = db.Column('amount', db.Integer)
    open = db.Column('open', db.Integer)
    side = db.Column('side', db.String(10))
    liquidation = db.Column('liquidation', db.Integer)
    failed = db.Column('failed', db.Boolean, default=False)
    order_exist = db.Column('order_exist', db.Boolean, default=False)
    order_id = db.Column('order_id', db.String(100))

    def __init__(self, apiKey, secret, balance=0, order_type='null', symbol='BTC/USD',
                 amount=0, open=0, side=0, liquidation=0, failed=False,
                 order_exist=False, order_id=0):
        self.apiKey = apiKey
        self.secret = secret
        self.balance = balance
        self.order_type = order_type
        self.symbol = symbol
        self.amount = amount
        self.open = open
        self.side = side
        self.liquidation = liquidation
        self.failed = failed
        self.order_exist = order_exist
        self.order_id = order_id


socketio = SocketIO(app, async_mode=None)
thread_lock = Lock()
thread = None


#@app.before_first_request
#def first_touch():
#    c = ClientModel.query.all()[-1]
#    db.session.delete(c)
#    db.session.commit()
#    db.create_all()


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You have to login first')
            return redirect(url_for('login'))
    return wrap


@app.route('/login/', methods=['GET', 'POST'])
def login():
    error = ''
    form = UserLoginForm(request.form)
    try:
        if request.method == 'POST':
            user = User.query.filter_by(username=form.username.data).first()
            if user.password == request.form['password']:
                session['logged_in'] = True
                session['username'] = request.form['username']

                flash("You are logged in as {}".format(session['username']))
                return redirect(url_for(''))
            else:
                error = 'Invalid credentials, try again'
        gc.collect()

        return render_template('login.html', error=error, form=form)
    except Exception as e:
        error = 'Invalid credentials, try again'
        return render_template('login.html', error=error, form=form)


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out!')
    gc.collect()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def hello_world():
    form = ClientForm(request.form)
    return render_template('index.html', async_mode=socketio.async_mode, form=form)


def reload_data():
    clients_db = ClientModel.query.all()
    clients = []
    for c in clients_db:
        clients.append(Client(
            apiKey=c.apiKey,
            secret=c.secret,
            failed=c.failed,
            order_id=c.order_id,
            order_exist=c.order_exist,
            amount=c.amount,
            open=c.open,
            side=c.side,
            order_type=c.order_type
        ))
    count = len(clients)
    data = {}
    if count:
        while True:
            try:
                tasks = [reload_loop.create_task(c.check_order()) for c in clients]
                wait_tasks = asyncio.wait(tasks)
                reload_loop.run_until_complete(wait_tasks)
                break
            except:
                print('[gen-data only] sleep for 3 seconds')
                socketio.sleep(3)
    counter = 0
    for i in range(count):
        if clients[i].auth:
            data[counter] = {}
            data[counter]['data'] = update_client_data(clients_db[i], clients[i].table_data())
            counter += 1
        else:
            db.session.delete(clients_db[i])
    db.session.commit()
    return data, counter


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
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('my event')
def handle_event(data):
    print('received json: ' + str(data))
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('market')
def market(data):
    print('**market**')
    run = check_for_blank_in_json_by_fields(data, 'amount')
    if not run[0]:
        emit('data error', {'msg': run[1], 'income': 'Market'})
        return
    clients = []
    clients_db = ClientModel.query.all()
    for c in clients_db:
        clients.append(Client(
            apiKey=c.apiKey,
            secret=c.secret,
            failed=c.failed,
            order_id=c.order_id,
            order_exist=c.order_exist,
            amount=c.amount,
            open=c.open,
            side=c.side,
            order_type=c.order_type
        ))
    while True:
        try:
            tasks = []
            any_not_exist = False
            for c in clients:
                if not c.order_exist or c.side != data['side']:
                    any_not_exist = True
                    tasks.append(reload_loop.create_task(c.create_market_order(side=data['side'], amount=data['amount'])))
            if not any_not_exist:
                tasks = [reload_loop.create_task(c.check_order()) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            reload_loop.run_until_complete(wait_tasks)
            break
        except:
            print('[market] sleep for 3 seconds')
            socketio.sleep(3)
    data = {}
    count = len(clients)
    counter = 0
    for i in range(count):
        if clients[i].auth:
            data[counter] = {}
            data[counter]['data'] = update_client_data(clients_db[i], clients[i].table_data())
            counter += 1
        else:
            db.session.delete(clients_db[i])
    db.session.commit()
    socketio.emit('reload-table', {'data': data, 'count': counter})


@socketio.on('stop')
def stop(data):
    print('**stop**')
    # emit('data error', {'msg': 'Not working yet', 'income': 'Stop'})
    # return
    run = check_for_blank_in_json_by_fields(data, 'amount', 'price')
    if not run[0]:
        emit('data error', {'msg': run[1], 'income': 'Stop'})
        return
    clients = []
    clients_db = ClientModel.query.all()
    for c in clients_db:
        clients.append(Client(
            apiKey=c.apiKey,
            secret=c.secret,
            failed=c.failed,
            order_id=c.order_id,
            order_exist=c.order_exist,
            amount=c.amount,
            open=c.open,
            side=c.side,
            order_type=c.order_type
        ))
    while True:
        try:
            tasks = []
            any_not_exist = False
            for c in clients:
                if not c.order_exist:
                    any_not_exist = True
                    tasks.append(reload_loop.create_task(c.create_stop_order(side=data['side'], amount=data['amount'], stopPx=data['price'])))
            if not any_not_exist:
                tasks = [reload_loop.create_task(c.check_order()) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            reload_loop.run_until_complete(wait_tasks)
            break
        except:
            print('[stop] sleep for 3 seconds')
            socketio.sleep(3)
    data = {}
    count = len(clients)
    counter = 0
    for i in range(count):
        if clients[i].auth:
            data[counter] = {}
            data[counter]['data'] = update_client_data(clients_db[i], clients[i].table_data())
            counter += 1
        else:
            db.session.delete(clients_db[i])
    db.session.commit()
    socketio.emit('reload-table', {'data': data, 'count': counter})


@socketio.on('limit')
def limit(data):
    print('**limit**')
    run = check_for_blank_in_json_by_fields(data, 'amount', 'price')
    if not run[0]:
        emit('data error', {'msg': run[1], 'income': 'Limit'})
        return
    clients = []
    clients_db = ClientModel.query.all()
    for c in clients_db:
        clients.append(Client(
            apiKey=c.apiKey,
            secret=c.secret,
            failed=c.failed,
            order_id=c.order_id,
            order_exist=c.order_exist,
            amount=c.amount,
            open=c.open,
            side=c.side,
            order_type=c.order_type
        ))
    while True:
        try:
            tasks = []
            any_not_exist = False
            for c in clients:
                if not c.order_exist:
                    any_not_exist = True
                    tasks.append(reload_loop.create_task(c.create_limit_order(side=data['side'], amount=data['amount'], price=data['price'])))
            if not any_not_exist:
                tasks = [reload_loop.create_task(c.check_order()) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            reload_loop.run_until_complete(wait_tasks)
            break
        except Exception as e:
            print(e)
            print('[limit] sleep for 3 seconds')
            socketio.sleep(3)
    data = {}
    count = len(clients)
    counter = 0
    for i in range(count):
        if clients[i].auth:
            data[counter] = {}
            data[counter]['data'] = update_client_data(clients_db[i], clients[i].table_data())
            counter += 1
        else:
            db.session.delete(clients_db[i])
    db.session.commit()
    socketio.emit('reload-table', {'data': data, 'count': counter})


@socketio.on('add-client')
def add_client(data):
    print('**add-client**')
    apiKey, secret = data['form'].split('&')
    apiKey = apiKey.split('=')[-1]
    secret = secret.split('=')[-1]
    form = ClientForm(apiKey=apiKey, secret=secret)
    if form.validate():
        clients = []
        for c in ClientModel.query.all():
            clients.append(Client(
                apiKey=c.apiKey,
                secret=c.secret,
                failed=c.failed,
                order_id=c.order_id,
                order_exist=c.order_exist,
                amount=c.amount,
                open=c.open,
                side=c.side,
                order_type=c.order_type
            ))
        if Client.check_if_already_exist(clients, {'apiKey': form.apiKey.data, 'secret': form.secret.data}):
            client = Client(
                form.apiKey.data,
                form.secret.data
            )
            clients.append(client)
            db.session.add(ClientModel(client.apiKey, client.secret))
            db.session.commit()

            count = len(clients)
            data = {}
            while True:
                try:
                    tasks = [reload_loop.create_task(c.check_order()) for c in clients]
                    wait_tasks = asyncio.wait(tasks)
                    reload_loop.run_until_complete(wait_tasks)
                    break
                except:
                    print('[add-client] sleep for 3 seconds')
                    socketio.sleep(3)

            clients_db = ClientModel.query.all()
            counter = 0
            for i in range(count):
                if clients[i].auth:
                    data[counter] = {}
                    data[counter]['data'] = update_client_data(clients_db[i], clients[i].table_data())
                    counter += 1
                else:
                    db.session.delete(clients_db[i])
            db.session.commit()
            socketio.emit('reload-table', {'data': data, 'count': counter})
            print({'status': 'ok!'})
            return
        print({'status': 'already exists!'})
        emit('data error', {'msg': 'already exists!', 'income': 'Client'})
        return
    print({'status': 'fail!'})
    emit('data error', {'msg': 'fail!', 'income': 'Client'})
    return


@socketio.on('rm-all-orders')
def rm_all_orders():
    print('**rm-all-orders**')
    clients = []
    clients_db = ClientModel.query.all()
    for c in clients_db:
        clients.append(Client(
            apiKey=c.apiKey,
            secret=c.secret,
            failed=c.failed,
            order_id=c.order_id,
            order_exist=c.order_exist,
            amount=c.amount,
            open=c.open,
            side=c.side,
            order_type=c.order_type
        ))
    while True:
        try:
            tasks = [reload_loop.create_task(c.rm_all_orders()) for c in clients]
            wait_tasks = asyncio.wait(tasks)
            reload_loop.run_until_complete(wait_tasks)
            break
        except:
            print('[rm-all-orders] sleep for 3 seconds')
            socketio.sleep(3)
    data = {}
    count = len(clients)
    counter = 0
    for i in range(count):
        if clients[i].auth:
            data[counter] = {}
            data[counter]['data'] = update_client_data(clients_db[i], clients[i].table_data())
            counter += 1
        else:
            db.session.delete(clients_db[i])
    db.session.commit()
    socketio.emit('reload-table', {'data': data, 'count': counter})


if __name__ == '__main__':
    app.config['SECRET_KEY'] = '123123abc'
    reload_loop = asyncio.get_event_loop()
    socketio.run(app, '0.0.0.0', 5000)
