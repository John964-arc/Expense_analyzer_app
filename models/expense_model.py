from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db_helper import db


# ─────────────────────────────────────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(80),  unique=True, nullable=False)
    email           = db.Column(db.String(120), unique=True, nullable=False)
    password_hash   = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    base_currency   = db.Column(db.String(3),   default='INR')
    created_at      = db.Column(db.DateTime,    default=datetime.utcnow)

    expenses      = db.relationship('Expense',      backref='owner',    lazy=True, cascade='all, delete-orphan')
    budgets       = db.relationship('Budget',        backref='owner',    lazy=True, cascade='all, delete-orphan')
    savings_goals = db.relationship('SavingsGoal',   backref='owner',    lazy=True, cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# ─────────────────────────────────────────────────────────────────────────────
# EXPENSE
# ─────────────────────────────────────────────────────────────────────────────

class Expense(db.Model):
    __tablename__ = 'expenses'

    id               = db.Column(db.Integer,     primary_key=True)
    user_id          = db.Column(db.Integer,     db.ForeignKey('users.id'), nullable=False)
    name             = db.Column(db.String(200), nullable=False)
    amount           = db.Column(db.Float,       nullable=False)
    category         = db.Column(db.String(50),  default='Other')
    date             = db.Column(db.DateTime,    default=datetime.utcnow)
    description      = db.Column(db.Text,        default='')
    receipt_image    = db.Column(db.String(255), nullable=True)
    # Multi-currency
    currency         = db.Column(db.String(3),   default='INR')
    converted_amount = db.Column(db.Float,       nullable=True)   # amount in user's base_currency
    # Recurring / subscription
    is_recurring     = db.Column(db.Boolean,     default=False)
    recurring_day    = db.Column(db.Integer,     nullable=True)   # day-of-month for reminder
    created_at       = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':               self.id,
            'name':             self.name,
            'amount':           self.amount,
            'category':         self.category,
            'date':             self.date.strftime('%Y-%m-%d') if self.date else None,
            'description':      self.description,
            'receipt_image':    self.receipt_image,
            'currency':         self.currency or 'INR',
            'converted_amount': self.converted_amount,
            'is_recurring':     self.is_recurring,
            'recurring_day':    self.recurring_day,
        }

    def __repr__(self):
        return f'<Expense {self.name}: {self.currency}{self.amount}>'


# ─────────────────────────────────────────────────────────────────────────────
# BUDGET
# ─────────────────────────────────────────────────────────────────────────────

class Budget(db.Model):
    __tablename__ = 'budgets'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category', 'month', 'year', name='uq_budget'),
    )

    id         = db.Column(db.Integer,    primary_key=True)
    user_id    = db.Column(db.Integer,   db.ForeignKey('users.id'), nullable=False)
    category   = db.Column(db.String(50), nullable=True)   # NULL = overall monthly budget
    month      = db.Column(db.Integer,   nullable=False)
    year       = db.Column(db.Integer,   nullable=False)
    amount     = db.Column(db.Float,     nullable=False)
    created_at = db.Column(db.DateTime,  default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':       self.id,
            'category': self.category,
            'month':    self.month,
            'year':     self.year,
            'amount':   self.amount,
        }

    def __repr__(self):
        cat = self.category or 'Overall'
        return f'<Budget {cat} {self.month}/{self.year}: ₹{self.amount}>'


# ─────────────────────────────────────────────────────────────────────────────
# SAVINGS GOAL
# ─────────────────────────────────────────────────────────────────────────────

class SavingsGoal(db.Model):
    __tablename__ = 'savings_goals'

    id            = db.Column(db.Integer,     primary_key=True)
    user_id       = db.Column(db.Integer,     db.ForeignKey('users.id'), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float,       nullable=False)
    saved_amount  = db.Column(db.Float,       default=0.0)
    target_date   = db.Column(db.Date,        nullable=True)
    icon          = db.Column(db.String(10),  default='🎯')
    color         = db.Column(db.String(7),   default='#6C63FF')
    is_completed  = db.Column(db.Boolean,     default=False)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    contributions = db.relationship('SavingsContribution', backref='goal',
                                    lazy=True, cascade='all, delete-orphan')

    @property
    def progress_pct(self) -> float:
        if self.target_amount <= 0:
            return 0.0
        return min(round((self.saved_amount / self.target_amount) * 100, 1), 100.0)

    @property
    def remaining(self) -> float:
        return max(self.target_amount - self.saved_amount, 0.0)

    def to_dict(self) -> dict:
        return {
            'id':            self.id,
            'name':          self.name,
            'target_amount': self.target_amount,
            'saved_amount':  self.saved_amount,
            'remaining':     self.remaining,
            'progress_pct':  self.progress_pct,
            'target_date':   self.target_date.isoformat() if self.target_date else None,
            'icon':          self.icon,
            'color':         self.color,
            'is_completed':  self.is_completed,
        }

    def __repr__(self):
        return f'<SavingsGoal {self.name}: {self.progress_pct}%>'


# ─────────────────────────────────────────────────────────────────────────────
# SAVINGS CONTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────

class SavingsContribution(db.Model):
    __tablename__ = 'savings_contributions'

    id      = db.Column(db.Integer,     primary_key=True)
    goal_id = db.Column(db.Integer,     db.ForeignKey('savings_goals.id'), nullable=False)
    user_id = db.Column(db.Integer,     db.ForeignKey('users.id'),         nullable=False)
    amount  = db.Column(db.Float,       nullable=False)
    note    = db.Column(db.String(255), nullable=True)
    date    = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':      self.id,
            'goal_id': self.goal_id,
            'amount':  self.amount,
            'note':    self.note,
            'date':    self.date.strftime('%Y-%m-%d') if self.date else None,
        }

    def __repr__(self):
        return f'<Contribution goal={self.goal_id} ₹{self.amount}>'
