from flask import Flask, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from functools import wraps
import bcrypt
from db import db

#create app
app= Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To disable modification tracking, which can be performance-heavy

#initialize extentions with the app
db.init_app(app)
migrate = Migrate(app, db)

from models import User, Wallet, Transaction, Beneficiary, TransactionSummary, Analytics

# Utility function to hash password
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Utility function to verify password
def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Unauthorized access'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            return jsonify({'message': 'Admin access only'}), 403
        return f(*args, **kwargs)
    return decorated_function


### USER AUTHENTICATION ROUTES ###

# User Registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    profile_image = data.get('profile_image', None)
    
    # Validate the input data
    if not all([username, email, password]):
        return jsonify({"error": "All fields are required!"}), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists!"}), 409

     # Create a new user and a wallet for the user
    hashed_password = hash_password(password)
    new_user = User(username=username, email=email, profile_image=profile_image)
    db.session.add(new_user)
    db.session.commit()

    new_wallet = Wallet(user_id=new_user.user_id, wallet_name="Default Wallet", balance=0.0, currency="USD")
    db.session.add(new_wallet)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully!",
        "user": new_user.to_dict(),
        "wallet": new_wallet.to_dict()   
    }), 201
  
# User Login Route 
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and verify_password(password, user.password):
        session['user_id'] = user.user_id
        return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200
    return jsonify({'message': 'Invalid email or password'}), 401

# User details route
@app.route('/user', methods=['GET'])
def get_user():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user:
        # Including wallet and profile image in the response
        return jsonify({
            "user": user.to_dict(),
            "wallet": user.wallet.to_dict() if user.wallet else None,
            "profile_image": user.profile_image
        }), 200
    return jsonify({"error": "User not found!"}), 404

# User Logout
@app.route('/logout', methods=['POST'])
def logout_user():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

### WALLET ROUTES ###
# Create a Wallet
@app.route('/wallet', methods=['POST'])
@login_required
def create_wallet():
    user = get_current_user()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    data = request.json
    wallet_name = data.get('wallet_name', 'My Wallet')
    new_wallet = Wallet(user_id=user.user_id, wallet_name=wallet_name)
    db.session.add(new_wallet)
    db.session.commit()
    return jsonify({'message': 'Wallet created successfully', 'wallet': new_wallet.to_dict()}), 201


# Fund Wallet
@app.route('/wallet/fund', methods=['POST'])
def fund_wallet():
    data = request.json
    wallet_id = data.get('wallet_id')
    amount = data.get('amount')

    wallet = Wallet.query.get(wallet_id)
    if wallet and wallet.fund_wallet(amount):
        db.session.commit()
        return jsonify({'message': 'Wallet funded successfully', 'balance': wallet.balance}), 200
    return jsonify({'message': 'Failed to fund wallet'}), 400


# Withdraw from Wallet
@app.route('/wallet/withdraw', methods=['POST'])
def withdraw_wallet():
    data = request.json
    wallet_id = data.get('wallet_id')
    amount = data.get('amount')

    wallet = Wallet.query.get(wallet_id)
    if wallet and wallet.withdraw(amount):
        db.session.commit()
        return jsonify({'message': 'Withdrawal successful', 'balance': wallet.balance}), 200
    return jsonify({'message': 'Failed to withdraw from wallet'}), 400

# Route to get User's Wallet
@app.route('/wallet', methods=['GET'])
def get_wallet():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user and user.wallet:
        return jsonify(user.wallet.to_dict()), 200
    return jsonify({"error": "Wallet not found!"}), 404

### TRANSACTION ROUTES ###

@app.route('/transaction', methods=['POST'])
@login_required
def handle_transaction():
    data = request.get_json()
    sender_wallet_id = data.get('sender_wallet_id')
    receiver_wallet_id = data.get('receiver_wallet_id')
    amount = data.get('amount')
    description = data.get('description')
    
    sender_wallet = Wallet.query.get(sender_wallet_id)
    receiver_wallet = Wallet.query.get(receiver_wallet_id)

    if not sender_wallet or not receiver_wallet:
        return jsonify({"error": "Invalid wallet IDs!"}), 400
    
    # Check balance and perform transaction
    transaction_fee_rate = 0.02
    transaction_fee = amount * transaction_fee_rate
    total_deduction = amount + transaction_fee

    if sender_wallet.balance < total_deduction:
        return jsonify({"error": "Insufficient funds!"}), 400

    # Proceed with transaction
    sender_wallet.balance -= total_deduction
    receiver_wallet.balance += amount

    transaction = Transaction(
        sender_wallet_id=sender_wallet_id,
        receiver_wallet_id=receiver_wallet_id,
        amount=amount,
        transaction_fee=transaction_fee,
        description=description
    )
    db.session.add(transaction)
    db.session.commit()

    return jsonify(transaction.to_dict()), 201


# Route to get all transactions of a user 
@app.route('/transactions', methods=['GET'])
def get_transactions():
    user_id = request.args.get('user_id')
    page = request.args.get('page', 1, type=int)
    user = User.query.get(user_id)
    if user:
        if user.wallet:  # Ensure the user has a wallet
            transactions = Transaction.query.filter(
                (Transaction.sender_wallet_id == user.wallet.wallet_id) |
                (Transaction.receiver_wallet_id == user.wallet.wallet_id)
            ).all()
            return jsonify([transaction.to_dict() for transaction in transactions]), 200
        else:
            return jsonify({"error": "User does not have an associated wallet!"}), 404
    return jsonify({"error": "User not found!"}), 404

### BENEFICIARY ROUTES ###
# Route to add a beneficiary
@app.route('/beneficiary', methods=['POST'])
def add_beneficiary():
    user = get_current_user()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')
    beneficiary_name = data.get('beneficiary_name')
    beneficiary_account = data.get('beneficiary_account')

    new_beneficiary = Beneficiary(
        user_id=user.user_id,
        beneficiary_name=beneficiary_name,
        beneficiary_account=beneficiary_account
    )
    db.session.add(new_beneficiary)
    db.session.commit()
    return jsonify({'message': 'Beneficiary added', 'beneficiary': new_beneficiary.to_dict()}), 201


# Route to get all beneficiaries of a user
@app.route('/beneficiaries', methods=['GET'])
def get_beneficiaries():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if user:
        beneficiaries = Beneficiary.query.filter_by(user_id=user_id).all()
        return jsonify([beneficiary.to_dict() for beneficiary in beneficiaries]), 200
    return jsonify({"error": "User not found!"}), 404


### ANALYTICS ROUTES ###

# Admin Route: Transaction Summary
@app.route('/admin/transaction-summary', methods=['GET'])
@admin_required
def get_transaction_summary():
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        return jsonify({'message': 'Unauthorized access'}), 403

    summary = TransactionSummary.query.all() 
    return jsonify([summary_item.to_dict() for summary_item in summary]), 200

# Admin Route: User Analytics 
@app.route('/admin/user-analytics', methods=['GET'])
@admin_required
def get_user_analytics():
    user_id = request.args.get('user_id')
    analytics = Analytics.query.filter_by(user_id=user_id).all()
    return jsonify([analytic.to_dict() for analytic in analytics]), 200

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)