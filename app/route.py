from flask import render_template, request, redirect, url_for, flash, session
from flask_socketio import emit
from functools import wraps
from threading import Lock
import sqlalchemy
import gc

from app.models import UserModel
from app.forms import UserLoginForm, ClientForm
from app import app, socketio, sentry

from bmex import check_for_blank_in_json_by_fields

from BmexIhar.views import TableIhar

# admin = UserModel('trademan', 'wen234man')
# db.session.add(admin)
# db.session.commit()

thread_lock = Lock()
table = None
thread = None


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You have to login first')
            return redirect(url_for('login'))
    return wrap


def table_loader(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        global table
        if table is None:
            table = TableIhar()
        return f(*args, **kwargs)
    return wrap


@app.before_first_request
def before_first_request():
    global table
    table = TableIhar()


@app.route('/login/', methods=['GET', 'POST'])
def login():
    error = ''
    form = UserLoginForm(request.form)
    try:
        if request.method == 'POST':
            user = UserModel.query.filter_by(username=form.username.data).first()
            if user.password == request.form['password']:
                session['logged_in'] = True
                session['username'] = request.form['username']

                flash("You are logged in as {}".format(session['username']))
                return redirect('/')
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
@table_loader
def hello_world():
    form = ClientForm(request.form)
    return render_template('index.html', async_mode=socketio.async_mode, form=form)


def background_data():
    while True:
        table.update_all()
        table.view()
        socketio.emit('reload-table', table.gen_data())
        socketio.sleep(45)


@socketio.on('connect')
@table_loader
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_data)
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('my event')
def handle_event(_):
    emit('my response', {'data': 'Connected', 'count': 0})


@socketio.on('order')
def order(data):
    run = check_for_blank_in_json_by_fields(data, 'amount')
    if not run[0]:
        emit('data error', {'msg': run[1], 'income': data['type']})
        return
    table.add_order(type=data['type'], side=data['side'], amount=data['amount'], price=data['price'])
    table.update_all()
    table.view()
    socketio.emit('reload-table', table.gen_data())


@socketio.on('add-client')
def add_client(data):
    key, secret = data['form'].split('&')
    key = key.split('=')[-1]
    secret = secret.split('=')[-1]
    form = ClientForm(apiKey=key, secret=secret)
    if form.validate():
        try:
            table.add_client(key, secret)
            table.update_all()
            table.view()
            socketio.emit('reload-table', table.gen_data())
            return
        except sqlalchemy.exc.IntegrityError:
            sentry.captureMessage({'status': 'already exists!'})
            emit('data error', {'msg': 'already exists!', 'income': 'Client'})
            return
    sentry.captureMessage({'status': 'fail! to create user'})
    emit('data error', {'msg': 'fail!', 'income': 'Client'})
    return


@socketio.on('rm-all-orders')
def rm_all_orders():
    table.close_all_orders()
    table.update_all()
    table.view()
    socketio.emit('reload-table', table.gen_data())


@socketio.on('reorder')
def reorder_failed(data):
    run = check_for_blank_in_json_by_fields(data, 'amount')
    if not run[0]:
        emit('data error', {'msg': run[1], 'income': data['type']})
        return
    table.add_failed_order(type=data['type'], side=data['side'], amount=data['amount'], price=data['price'])
    table.update_all()
    table.view()
    socketio.emit('reload-table', table.gen_data())
