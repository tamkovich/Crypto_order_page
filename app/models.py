from app import db


class ClientModel(db.Model):

    __tablename__ = 'client'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    apiKey = db.Column(db.String(100), unique=True)
    secret = db.Column(db.String(100), unique=True)
    failed = db.Column('failed', db.Boolean, default=False)
    order_exist = db.Column('order_exist', db.Boolean, default=False)

    orders = db.relationship("OrderModel", backref="client", lazy=True)

    def __init__(self, apiKey, secret, failed=False, order_exist=False):
        self.apiKey = apiKey
        self.secret = secret
        self.open = open
        self.failed = failed
        self.order_exist = order_exist


class OrderModel(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_exchange_id = db.Column(db.String(100))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)


class UserModel(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), unique=True)

    def __init__(self, username, password):
        self.username = username
        self.password = password
