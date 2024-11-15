from flask import Flask, request, jsonify, redirect, url_for, session,make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
from flask_login import UserMixin
from functools import wraps
import bcrypt
from db import db
from flask_cors import CORS


#create app
app= Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///app.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['UPLOAD_FOLDER'] = 'static/uploads/profile_images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
CORS(app)

#initialize extentions with the app
db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

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

# Helper function to check if the file is an allowed image
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

### USER AUTHENTICATION ROUTES ###

# User Registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    phone_number = data.get('phone_number')
    password = data.get('password')
    profile_image = data.get('profile_image', None)
    
    # Validate the input data
    if not all([username, email, password, phone_number]):
        return jsonify({"error": "All fields are required!"}), 400

    # Check if email or phone number already exists
    existing_user = User.query.filter((User.email == email) | (User.phone_number == phone_number)).first()
    if existing_user:
        return jsonify({'error': 'User with this email or phone number already exists'}), 409

     # Create a new user and a wallet for the user

    new_user = User(username=username, email=email, phone_number=phone_number, password=password, profile_image=profile_image)
    db.session.add(new_user)
    db.session.commit()

    new_wallet = Wallet(user_id=new_user.user_id, wallet_name="Default Wallet", balance=0.0)
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
    if user and user.check_password(password):
        session['user_id'] = user.user_id
        return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200
    return jsonify({'message': 'Invalid email or password'}), 401

# User details route
@app.route('/user/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get(id)
    wallets = Wallet.query.filter_by(user_id=id).all()  
    
    if user:
        wallets_data = [wallet.to_dict() for wallet in wallets]
        return jsonify({
            "user": user.to_dict(),
            "wallets": wallets_data,  
            "profile_image": user.profile_image 
        }), 200
    return jsonify({"error": "User not found!"}), 404


# Getting all Users
from flask import jsonify, request

@app.route("/users", methods=['GET'])
def get_users():
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Query and paginate users
        pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
        users = [user.to_dict() for user in pagination.items]

        # Construct response
        response = {
            "users": users,
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page,
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": "Something went wrong", "details": str(e)}), 500

    

# update profile
@app.route('/update-profile/<int:user_id>', methods=['POST'])
def update_profile(user_id):
    # Check if the user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required!"}), 401
    # Ensure the logged-in user matches the user_id in the URL
    if session['user_id'] != user_id:
        return jsonify({"error": "You can only update your own profile"}), 403

    # Fetch the user from the database
    user = User.query.get_or_404(user_id)

    # Handle form data, image uploads, etc.
    username = request.form.get('username')
    email = request.form.get('email')
    profile_image = request.files.get('profile_image')

    # Update user profile
    user.username = username
    user.email = email
    if profile_image:
        # Update the profile image path (handle the image upload)
        user.profile_image = save_image(profile_image)  # Assuming save_image() handles file saving

    db.session.commit()

    return jsonify({"message": "Profile updated successfully!"}), 200

# Get user profile
@app.route('/profile/<int:user_id>', methods=['GET'])
def view_profile(user_id):
    if 'user_id' not in session:
        return jsonify({"error": "Authentication required!"}), 401

    # Ensure the logged-in user matches the user_id in the URL
    if session['user_id'] != user_id:
        return jsonify({"error": "You can only view your own profile"}), 403
    # Fetch the user from the database
    user = User.query.get_or_404(user_id)

    return jsonify({
        "username": user.username,
        "email": user.email,
        "profile_image": user.profile_image
    })



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
@app.route('/wallet/<int:id>', methods=['GET'])
def get_wallet(id):
    user = User.query.get(id)
    wallets = Wallet.query.filter_by(user_id=id).all()  
    if user:
        wallets_data = [wallet.to_dict() for wallet in wallets]
        return jsonify({
            "wallets": wallets_data,   
        }), 200
    return jsonify({"error": "user not found!"}), 404

### TRANSACTION ROUTES ###

@app.route('/transaction', methods=['POST'])
@login_required
def handle_transaction():
    user = get_current_user()
    user_id = user.user_id
    data = request.get_json()
    sender_wallet_id = data.get('sender_wallet_id')
    receiver_wallet_id = data.get('receiver_wallet_id')
    amount = data.get('amount')
    description = data.get('description', '')
    
    user_id = session.get('user_id')

    # Validate input data
    if not all([sender_wallet_id, receiver_wallet_id, amount]):
        return jsonify({"error": "Missing required fields!"}), 400
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero!"}), 400
   
    sender_wallet = Wallet.query.get(sender_wallet_id)
    receiver_wallet = Wallet.query.get(receiver_wallet_id)

    if not sender_wallet or not receiver_wallet:
        return jsonify({"error": "Invalid wallet IDs!"}), 400
    
     # Check balance and perform transaction
    if amount  >=0 and amount <= 500 :
        transaction_fee = 0
    elif amount >=501 and amount <= 10000:
        transaction_fee = 42
    elif amount >=100001 and amount <= 50000:
        transaction_fee = 62
    elif amount >=50001 and amount <= 60000:
        transaction_fee = 82
    elif amount >= 60001 and amount <=70000:
        transaction_fee = 92
    else: transaction_fee = amount*0.002

    total_deduction = amount + transaction_fee

    if sender_wallet.balance < total_deduction:
        return jsonify({"error": "Insufficient funds!"}), 400

    # Proceed with transaction
    sender_wallet.balance -= total_deduction
    receiver_wallet.balance += amount

    transaction = Transaction(
        user_id=user_id,
        sender_wallet_id=sender_wallet_id,
        receiver_wallet_id=receiver_wallet_id,
        amount=amount,
        transaction_fee=transaction_fee,
        description=description
    )
    db.session.add(transaction)
    db.session.commit()

    

    return jsonify(transaction.to_dict()), 201

# Route for reversing a transaction
@app.route('/transaction/reverse/<int:transaction_id>', methods=['POST'])

def reverse_transaction(transaction_id):

    if 'user_id' not in session:
        return jsonify({"error": "Authentication required!"}), 401

    # Fetch current user
    current_user_id = session['user_id']
    current_user = User.query.get(current_user_id)
     # Fetch the transaction to be reversed
    transaction = Transaction.query.get(transaction_id)

    # Check if the transaction exists
    if not transaction:
        return jsonify({"error": "Transaction not found!"}), 404

    # Ensure the transaction is not already reversed
    if transaction.is_reversed:
        return jsonify({"error": "Transaction has already been reversed!"}), 400

    # Ensure the current user is the one who performed the transaction
    if transaction.user_id != current_user.user_id:
        return jsonify({"error": "You cannot reverse a transaction that you did not initiate!"}), 403

    # Check if sender and receiver wallets are valid
    sender_wallet = Wallet.query.get(transaction.sender_wallet_id)
    receiver_wallet = Wallet.query.get(transaction.receiver_wallet_id)

    if not sender_wallet or not receiver_wallet:
        return jsonify({"error": "Invalid wallet IDs associated with this transaction!"}), 400

    # Reverse the transaction by updating the wallets and the transaction status
    # 1. Perform reversal on wallets (subtract the amount from the receiver and add back to the sender)
    if receiver_wallet.balance < transaction.amount:
        return jsonify({"error": "Receiver does not have sufficient funds for reversal!"}), 400

    try:
        # Reverse the wallet balances
        sender_wallet.balance += transaction.amount
        receiver_wallet.balance -= transaction.amount

        # Mark the transaction as reversed
        transaction.reverse_transaction()
        transaction.status = 'reversed'

        # Commit the transaction
        db.session.commit()

        return jsonify({
            "message": "Transaction reversed successfully!",
            "transaction": transaction.to_dict()
        }), 200
        

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error occurred: {str(e)}"}), 500

# Route to get all transactions of a user 
@app.route('/transactions/<int:id>', methods=['GET'])
def get_transactions(id):
    user = User.query.get(id)
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
    beneficiary_email = data.get('beneficiary_email')

    # Check if beneficiary email exists in the system
    beneficiary = User.query.filter_by(email=beneficiary_email).first()
    if not beneficiary:
        return jsonify({'message': 'Beneficiary email not found'}), 404
    
     # Create a new beneficiary record
    new_beneficiary = Beneficiary(
        user_id=user.user_id,
        beneficiary_email=beneficiary_email
    )
   
    db.session.add(new_beneficiary)
    db.session.commit()

    return jsonify({'message': 'Beneficiary added', 'beneficiary': new_beneficiary.to_dict()}), 201


# Route to get all beneficiaries of a user
@app.route('/beneficiaries/<int:id>', methods=['GET'])
def get_beneficiaries(id):
    user = User.query.get(id)
    if user:
        beneficiaries = Beneficiary.query.filter_by(user_id=id).all()
        return jsonify([beneficiary.to_dict() for beneficiary in beneficiaries]), 200
    return jsonify({"error": "User not found!"}), 404

# Route to delete a beneficiary
@app.route('/beneficiary/<int:beneficiary_id>', methods=['DELETE'])
def delete_beneficiary(beneficiary_id):
    # Check if the user is authenticated (get the current user, similar to the add beneficiary route)
    user = get_current_user()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.get_json()
    beneficiary_email = data.get('beneficiary_email')

    if not beneficiary_email:
        return jsonify({'message': 'Beneficiary email is required'}), 400

    # Find the beneficiary by using email and ensure it was added the current user
    beneficiary = Beneficiary.query.filter_by(user_id=user.user_id, beneficiary_email=beneficiary_email).first()

    if not beneficiary:
        return jsonify({'message': 'Beneficiary not found'}), 404

    # Perform a soft delete (set 'is_active' to False)
    beneficiary.soft_delete()
    
    # Commit the changes to the database
    db.session.commit()

    # Return a success message
    return jsonify({'message': 'Beneficiary deleted successfully', 'beneficiary': beneficiary.to_dict()}), 200

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