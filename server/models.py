# models.py
from datetime import datetime
import bcrypt
from db import db  # Import db instance from db.py

# User Model
class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    wallets = db.relationship('Wallet', backref='user', cascade="all, delete-orphan")
    beneficiaries = db.relationship('Beneficiary', backref='user', cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

# Wallet Model
class Wallet(db.Model):
    __tablename__ = 'wallets'

    wallet_id = db.Column(db.Integer, primary_key=True)
    wallet_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='Kes')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.user_wallet_id', backref='user_wallet', cascade="all, delete-orphan")
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.beneficiary_wallet_id', backref='beneficiary_wallet', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'wallet_id': self.wallet_id,
            'wallet_name': self.wallet_name,
            'user_id': self.user_id,
            'balance': self.balance,
            'currency': self.currency,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

# Beneficiary Model
class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    beneficiary_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'beneficiary_id': self.beneficiary_id,
            'user_id': self.user_id,
            'wallet_id': self.wallet_id,
            'added_at': self.added_at
        }

# Transaction Model
class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.Integer, primary_key=True)
    user_wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    beneficiary_wallet_id = db.Column(db.Integer, db.ForeignKey('beneficiaries.beneficiary_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending..')
    transaction_fee = db.Column(db.Float, nullable=True)
    description = db.Column(db.String(200))

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'user_wallet_id': self.user_wallet_id,
            'beneficiary_wallet_id': self.beneficiary_wallet_id,
            'amount': self.amount,
            'transaction_date': self.transaction_date,
            'status': self.status,
            'transaction_fee': self.transaction_fee,
            'description': self.description
        }
