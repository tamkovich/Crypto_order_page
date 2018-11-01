from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask import Flask

from raven.contrib.flask import Sentry
import logging

from private.config_sentry import dsn
from private.db import POSTGRES

app = Flask(__name__)
app.config['SECRET_KEY'] = 'adminadmin'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode=None)
sentry = Sentry(
    app, logging=True, level=logging.ERROR,
    logging_exclusions=("logger1", "logger2"), dsn=dsn
)

from app import route
