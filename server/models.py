from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from db import db
import uuid

class User(db.Model):
    __tablename__= 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone_number = db.Column(db.String(15), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)
    profile_image = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')  
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
     
    # Relationships to other models with cascade options
    wallet = db.relationship('Wallet', backref='owner', uselist=False, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")
    beneficiaries = db.relationship('Beneficiary', backref='user', lazy=True, cascade="all, delete-orphan")

    def __init__(self, username, email,phone_number, password, profile_image=None):
        self.username = username
        self.email = email
        self.phone_number = phone_number
        self.profile_image = profile_image
        self.set_password(password)
    
    # Set password with bcrypt hashing
    def set_password(self, password):
       self.password = generate_password_hash(password) 
    # Check password against hashed version
    def check_password(self, password):
        return check_password_hash(self.password, password)
    # Update profile
    def update_profile(self, username=None, email=None, profile_image=None):
        if username:
            self.username = username
        if email:
            self.email = email
        if profile_image:
            self.profile_image = profile_image


    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number,
            'role': self.role,
            'status': self.status,
            'profile_image': self.profile_image,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


# Wallet Model - Tracks user balances and currency
class Wallet(db.Model):
    __tablename__ = 'wallets'

    wallet_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    wallet_name = db.Column(db.String(50), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='USD')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Transactions associated with this wallet
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_wallet_id', backref='sender_wallet', cascade="all, delete-orphan")
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_wallet_id', backref='receiver_wallet', cascade="all, delete-orphan")
    
    # Fund wallet method
    def fund_wallet(self, amount):
        if amount > 0:
            self.balance += amount
            return True
        raise ValueError("Amount must be greater than zero")

    # Withdraw from wallet
    def withdraw(self, amount):
        if amount > 0 and self.balance >= amount:
            self.balance -= amount
            return True
        raise ValueError("Insufficient balance or invalid amount")

    def to_dict(self):
        return {
            'wallet_id': self.wallet_id,
            'user_id': self.user_id,
            'wallet_name': self.wallet_name,
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
    beneficiary_email = db.Column(db.String(100), nullable=False, unique=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # soft delete
    def soft_delete(self):
        self.is_active = False

    def to_dict(self):
        return {
            'beneficiary_id': self.beneficiary_id,
            'user_id': self.user_id,
            'beneficiary_email': self.beneficiary_email,
            'added_at': self.added_at,
            'is_active': self.is_active
        }  
    

# Transaction Model - Logs transactions between wallets
class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.String(36), primary_key=True)
    sender_wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    receiver_wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.wallet_id'), nullable=False)
    recipient_email = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False) 
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='completed')
    balance_after_transaction = db.Column(db.Float, nullable=True)
    transaction_type = db.Column(db.String(20), nullable=False)
    transaction_fee = db.Column(db.Float, nullable=True)
    description = db.Column(db.String(200))
    is_reversed = db.Column(db.Boolean, default=False)

    # Reverse transaction and adjust balances
    def reverse_transaction(self):
        sender_wallet = Wallet.query.get(self.sender_wallet_id)
        receiver_wallet = Wallet.query.get(self.receiver_wallet_id)

        if sender_wallet and receiver_wallet and not self.is_reversed:
            # Reverse the transaction by crediting the sender and debiting the receiver
            sender_wallet.balance += self.amount
            receiver_wallet.balance -= self.amount
            self.is_reversed = True

            try:
                db.session.add(sender_wallet)
                db.session.add(receiver_wallet)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                raise ValueError("Failed to reverse the transaction due to integrity error.")


    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'sender_wallet_id': self.sender_wallet_id,
            'receiver_wallet_id': self.receiver_wallet_id,
            'user_id': self.user_id,
            'recipient_email': self.recipient_email,
            'amount': self.amount,
            'transaction_date': self.transaction_date,
            'status': self.status,
            'transaction_fee': self.transaction_fee,
            'balance_after_transaction': self.balance_after_transaction,
            'transaction_type': self.transaction_type,
            'description': self.description,
            'is_reversed': self.is_reversed
        }
    
    @classmethod
    def create_transaction(cls, sender_wallet, receiver_wallet, user_id, amount, description=None, recipient_email=None, transaction_fee=Decimal('0.0'), transaction_type='payment'):
        # Generate a unique transaction reference using UUID
        
        transaction_reference = str(uuid.uuid4())

         # Convert amount to Decimal for accuracy
        amount = Decimal(amount)
        transaction_fee = Decimal(transaction_fee)
        total_amount = amount + transaction_fee

        if sender_wallet.balance < total_amount:
            raise ValueError("Insufficient funds")

        # Deduct the total amount from sender's wallet and add to reciever
        sender_wallet.balance -= total_amount
        receiver_wallet.balance += amount

        # Create a transaction record
        transaction = cls(
            transaction_id=transaction_reference,
            sender_wallet_id=sender_wallet.wallet_id,
            receiver_wallet_id=receiver_wallet.wallet_id,
            user_id=user_id,
            recipient_email=recipient_email,
            amount=amount,
            transaction_fee=transaction_fee,
            balance_after_transaction=sender_wallet.balance,
            transaction_type=transaction_type,
            description=description,
            status='completed'
        )

        # Save changes to the database
        try:
            with db.session.begin_nested():
                db.session.add(sender_wallet)
                db.session.add(receiver_wallet)
                db.session.add(transaction)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Transaction failed: {str(e)}")
        
        return transaction

    @staticmethod
    def get_all_transactions():
        # Fetch all transactions sorted by the most recent
        transactions = Transaction.query.order_by(Transaction.transaction_date.desc()).all()
        return [transaction.to_dict() for transaction in transactions]

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
    period = db.Column(db.String(50))  # e.g., 'monthly', 'quarterly'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'transaction_count': self.transaction_count,
            'total_spent': self.total_spent,
            'total_received': self.total_received,
            'period': self.period
        }

