from flask import Flask, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
from db import db

#create app
app= Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To disable modification tracking, which can be performance-heavy

#initialize extentions with the app
db.init_app(app)

from models import User, Wallet, Transaction, Beneficiary, TransactionSummary, Analytics
# User Registration Route

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Check if user already exists
    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists!"}), 400

    # Create new user
    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully!"}), 201

# User Login Route 
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return jsonify({"message": "Login successful!"}), 200
    else:
        return jsonify({"error": "Invalid username or password!"}), 401

# Route to get User's Wallet
@app.route('/wallet', methods=['GET'])
def get_wallet():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user and user.wallet:
        return jsonify(user.wallet.to_dict()), 200
    return jsonify({"error": "Wallet not found!"}), 404

 # Route to create a Transaction (Money Transfer) with 2% transaction fee
@app.route('/transaction', methods=['POST'])
def create_transaction():
    data = request.get_json()
    sender_wallet_id = data.get('sender_wallet_id')
    receiver_wallet_id = data.get('receiver_wallet_id')
    amount = data.get('amount')
    description = data.get('description')

    #Transaction fee rate
    transaction_fee_rate = 0.02
    transaction_fee = amount * transaction_fee_rate
    total_deduction = amount + transaction_fee  # Total amount to deduct from the sender

    # Retrieve wallets 
    sender_wallet = Wallet.query.get(sender_wallet_id)
    receiver_wallet = Wallet.query.get(receiver_wallet_id)

    if not sender_wallet or not receiver_wallet:
        return jsonify({"error": "Invalid wallet IDs!"}), 400

    # Ensure sender has enough balance
    if sender_wallet.balance < amount:
        return jsonify({"error": "Insufficient balance!"}), 400

    # Create transaction
    transaction = Transaction(
        sender_wallet_id=sender_wallet.wallet_id,
        receiver_wallet_id=receiver_wallet.wallet_id,
        amount=amount,
        description=description,
        fee=transaction_fee
    )

    # Update wallet balances
    sender_wallet.balance -= amount
    receiver_wallet.balance += amount

    # Commit changes to DB 
    db.session.add(transaction)
    db.session.commit()

    return jsonify(transaction.to_dict()), 201

# Route to get all transactions of a user 
@app.route('/transactions', methods=['GET'])
def get_transactions():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user:
        transactions = Transaction.query.filter((Transaction.sender_wallet_id == user.wallet.wallet_id) |
                                                 (Transaction.receiver_wallet_id == user.wallet.wallet_id)).all()
        return jsonify([transaction.to_dict() for transaction in transactions]), 200
    return jsonify({"error": "User not found!"}), 404

# Route to add a beneficiary
@app.route('/beneficiary', methods=['POST'])
def add_beneficiary():
    data = request.get_json()
    user_id = data.get('user_id')
    beneficiary_name = data.get('beneficiary_name')
    beneficiary_account = data.get('beneficiary_account')

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found!"}), 404

    beneficiary = Beneficiary(user_id=user_id, beneficiary_name=beneficiary_name, beneficiary_account=beneficiary_account)
    db.session.add(beneficiary)
    db.session.commit()
    return jsonify(beneficiary.to_dict()), 201

# Route to get all beneficiaries of a user
@app.route('/beneficiaries', methods=['GET'])
def get_beneficiaries():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user:
        beneficiaries = Beneficiary.query.filter_by(user_id=user_id).all()
        return jsonify([beneficiary.to_dict() for beneficiary in beneficiaries]), 200
    return jsonify({"error": "User not found!"}), 404

# Admin Route: Transaction Summary
@app.route('/admin/transaction-summary', methods=['GET'])
def get_transaction_summary():
    summary = TransactionSummary.query.all() 
    return jsonify([summary_item.to_dict() for summary_item in summary]), 200

# Admin Route: User Analytics 
@app.route('/admin/user-analytics', methods=['GET'])
def get_user_analytics():
    user_id = request.args.get('user_id')
    analytics = Analytics.query.filter_by(user_id=user_id).all()
    return jsonify([analytic.to_dict() for analytic in analytics]), 200

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
