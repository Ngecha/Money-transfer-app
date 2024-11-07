from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from db import db

class User(db.Model):
    __tablename__= 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

     
    # Relationships to other models with cascade options
    wallet = db.relationship('Wallet', backref='owner', uselist=False, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")
    beneficiaries = db.relationship('Beneficiary', backref='user', lazy=True, cascade="all, delete-orphan")

    # Set password with bcrypt hashing
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Check password against hashed version
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


# Wallet Model - Tracks user balances and currency
class Wallet(db.Model):
    __tablename__ = 'wallets'

    wallet_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Transactions associated with this wallet
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_wallet_id', backref='sender_wallet', cascade="all, delete-orphan")
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_wallet_id', backref='receiver_wallet', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'wallet_id': self.wallet_id,
            'user_id': self.user_id,
            'balance': self.balance,
            'currency': self.currency,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
# Beneficiary Model - Stores information on user's beneficiaries
class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    beneficiary_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    beneficiary_name = db.Column(db.String(100), nullable=False)
    beneficiary_account = db.Column(db.String(100), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'beneficiary_id': self.beneficiary_id,
            'user_id': self.user_id,
            'beneficiary_name': self.beneficiary_name,
            'beneficiary_account': self.beneficiary_account,
            'added_at': self.added_at
        }  
    

# Transaction Model - Logs transactions between wallets
class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.Integer, primary_key=True)
    sender_wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    receiver_wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    transaction_fee = db.Column(db.Float, nullable=True)
    description = db.Column(db.String(200))

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'sender_wallet_id': self.sender_wallet_id,
            'receiver_wallet_id': self.receiver_wallet_id,
            'amount': self.amount,
            'transaction_date': self.transaction_date,
            'status': self.status,
            'transaction_fee': self.transaction_fee,
            'description': self.description
        }
    

# TransactionSummary Model - Provides summary analytics for admins
class TransactionSummary(db.Model):
    __tablename__ = 'transaction_summary'

    id = db.Column(db.Integer, primary_key=True)
    total_transactions = db.Column(db.Integer)
    total_amount = db.Column(db.Float)
    total_fees = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'total_transactions': self.total_transactions,
            'total_amount': self.total_amount,
            'total_fees': self.total_fees,
            'timestamp': self.timestamp
        }
    

# Analytics Model - Tracks activity and financial metrics for each user
class Analytics(db.Model):
    __tablename__ = 'analytics'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    transaction_count = db.Column(db.Integer)
    total_spent = db.Column(db.Float)
    total_received = db.Column(db.Float)
    profit_generated = db.Column(db.Float)
    period = db.Column(db.String(50))  # e.g., 'monthly', 'quarterly'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'transaction_count': self.transaction_count,
            'total_spent': self.total_spent,
            'total_received': self.total_received,
            'profit_generated': self.profit_generated,
            'period': self.period
        }


