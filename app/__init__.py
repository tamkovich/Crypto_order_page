from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask import Flask

from settings import config

app = Flask(__name__)
app.config['SECRET_KEY'] = 'adminadmin'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://%(user)s:\
%(pw)s@%(host)s:%(port)s/%(db)s' % config['db']
db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode=None)

from app import route
