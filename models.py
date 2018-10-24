from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    pass
