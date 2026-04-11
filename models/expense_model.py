from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db_helper import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    expenses      = db.relationship('Expense', backref='owner', lazy=True,
                                    cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Expense(db.Model):
    __tablename__ = 'expenses'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name          = db.Column(db.String(200), nullable=False)
    amount        = db.Column(db.Float, nullable=False)
    category      = db.Column(db.String(50), default='Other')
    date          = db.Column(db.DateTime, default=datetime.utcnow)
    description   = db.Column(db.Text, default='')
    receipt_image = db.Column(db.String(255), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':            self.id,
            'name':          self.name,
            'amount':        self.amount,
            'category':      self.category,
            'date':          self.date.strftime('%Y-%m-%d') if self.date else None,
            'description':   self.description,
            'receipt_image': self.receipt_image,
        }

    def __repr__(self):
        return f'<Expense {self.name}: ₹{self.amount}>'
