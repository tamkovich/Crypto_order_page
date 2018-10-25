from mvc.app import db


class ClientModel(db.Model):

    __tablename__ = 'client'
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

    orders = db.relationship("Order", backref="client", lazy=True)

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


class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_exchange_id = db.Column(db.String(100))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

    def __init__(self, order_exchange_id):
        self.order_exchange_id = order_exchange_id


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), unique=True)
