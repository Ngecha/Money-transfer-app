from flask import Flask, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from flask_login import UserMixin
from functools import wraps
import bcrypt
from db import db

#create app
app= Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
# postgresql://moneytransferapp_1v08_user:MPa5iqmH2jkd0oQr3tWM3eTfhSFjLMC2@dpg-csq3t3aj1k6c73824rg0-a.oregon-postgres.render.com/moneytransferapp_1v08
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['UPLOAD_FOLDER'] = 'static/uploads/profile_images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

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

@app.route('/')
def home():
    return "Welcome to the Money Transfer App!"

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
# Fund Wallet Route
@app.route('/wallet/fund', methods=['POST'])
@login_required
def fund_wallet():
    user = get_current_user()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.json
    wallet_id = data.get('wallet_id')
    amount = data.get('amount')

    # Validate the input
    if not wallet_id or not amount or amount <= 0:
        return jsonify({'error': 'Invalid wallet ID or amount'}), 400

    wallet = Wallet.query.filter_by(user_id=user.user_id, wallet_id=wallet_id).first()
    if not wallet:
        return jsonify({'error': 'Wallet not found'}), 404

    try:
        # Fund the wallet
        wallet.balance += amount
        db.session.commit()
        return jsonify({'message': 'Wallet funded successfully', 'balance': wallet.balance}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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

@app.route('/send-money', methods=['POST'])
@login_required
def send_money():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    beneficiary_email = data.get('beneficiary_email')
    amount = data.get('amount')
    description = data.get('description', '')

    # Validate input
    if not beneficiary_email or not amount:
        return jsonify({"error": "Beneficiary email and amount are required"}), 400
    if not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    try:
        # Fetch sender's wallet
        sender_wallet = Wallet.query.filter_by(user_id=user.user_id).first()
        if not sender_wallet:
            return jsonify({"error": "Sender wallet not found"}), 404

        # Fetch beneficiary
        beneficiary = Beneficiary.query.filter_by(beneficiary_email=beneficiary_email, is_active=True).first()
        if not beneficiary:
            return jsonify({"error": "Beneficiary not found or inactive"}), 404

        # Fetch receiver's wallet
        receiver_wallet = Wallet.query.filter_by(user_id=beneficiary.user_id).first()
        if not receiver_wallet:
            return jsonify({"error": "Receiver wallet not found"}), 404

        # Transaction fee calculation
        transaction_fee = 0
        if 0 < amount <= 500:
            transaction_fee = 0
        elif 501 <= amount <= 10000:
            transaction_fee = 42
        elif 10001 <= amount <= 50000:
            transaction_fee = 62
        elif 50001 <= amount <= 60000:
            transaction_fee = 82
        elif 60001 <= amount <= 70000:
            transaction_fee = 92
        else:
            transaction_fee = amount * 0.002

        total_deduction = amount + transaction_fee

        # Check if sender has enough funds
        if sender_wallet.balance < total_deduction:
            return jsonify({"error": "Insufficient funds"}), 400

        # Start the transaction explicitly
        db.session.begin()

        # Deduct from sender
        sender_wallet.balance -= total_deduction
        db.session.add(sender_wallet)

        # Credit receiver
        receiver_wallet.balance += amount
        db.session.add(receiver_wallet)

        # Create the transaction record
        transaction = Transaction.create_transaction(
            sender_wallet=sender_wallet,
            receiver_wallet=receiver_wallet,
            user_id=user.user_id,
            amount=amount,
            description=description,
            recipient_email=beneficiary_email,
            transaction_fee=transaction_fee,
            transaction_type='payment'
        )

        # Commit the transaction
        db.session.commit()
        db.session.remove()

        return jsonify(transaction.to_dict()), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        db.session.remove()
        return jsonify({"error": str(e)}), 500


# Route for reversing a transaction
@app.route('/transaction/reverse/<int:transaction_id>', methods=['POST'])
@login_required
def reverse_transaction(transaction_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    try:
        # Fetch the transaction to be reversed
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404

        # Ensure the transaction is not already reversed
        if transaction.is_reversed:
            return jsonify({"error": "Transaction already reversed"}), 400

        # Verify if the current user is the initiator of the transaction
        if transaction.user_id != user.user_id:
            return jsonify({"error": "Unauthorized to reverse this transaction"}), 403

        # Fetch sender and receiver wallets
        sender_wallet = Wallet.query.get(transaction.sender_wallet_id)
        receiver_wallet = Wallet.query.get(transaction.receiver_wallet_id)

        if not sender_wallet or not receiver_wallet:
            return jsonify({"error": "Wallets involved not found"}), 404

        # Reverse the transaction
        with db.session.begin():
            sender_wallet.balance += transaction.amount + transaction.transaction_fee
            receiver_wallet.balance -= transaction.amount
            transaction.is_reversed = True

            db.session.add(sender_wallet)
            db.session.add(receiver_wallet)
            db.session.add(transaction)

        return jsonify({"message": "Transaction reversed successfully"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

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
# Add Beneficiary Route
@app.route('/beneficiary/add', methods=['POST'])
@login_required
def add_beneficiary():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    beneficiary_email = data.get('beneficiary_email')
    

    # Validate the input
    if not beneficiary_email :
        return jsonify({"error": "Beneficiary email is required"}), 400

    # Check if the beneficiary already exists for this user
    existing_beneficiary = Beneficiary.query.filter_by(
        user_id=user.user_id, beneficiary_email=beneficiary_email).first()
    if existing_beneficiary:
        return jsonify({"error": "Beneficiary already exists"}), 409

    try:
        # Add new beneficiary
        new_beneficiary = Beneficiary(
            user_id=user.user_id,
            beneficiary_email=beneficiary_email,
            is_active=True
        )
        db.session.add(new_beneficiary)
        db.session.commit()
        return jsonify({"message": "Beneficiary added successfully", "beneficiary": new_beneficiary.to_dict()}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


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

# Route to fetch transaction history for a specific user
@app.route('/transactions/history', methods=['GET'])
@login_required
def get_transaction_history():
    # Fetch the currently logged-in user from session
    user_id = session.get('user_id')

    # Check if the user is authenticated
    if not user_id:
        return jsonify({'message': 'Unauthorized access. Please log in.'}), 401

    # Get the optional 'date' parameter from query string
    date = request.args.get('date')  # Format: 'YYYY-MM-DD'

    # Validate the 'date' parameter
    if not date:
        return jsonify({'message': 'Date parameter is required. Format: YYYY-MM-DD.'}), 400

    try:
        # Parse the date into a datetime object for comparison
        date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # Build the query to fetch transactions related to the user
    query = Transaction.query.filter_by(user_id=user_id, transaction_date=date)

    # Fetch the transactions from the database
    transactions = query.order_by(Transaction.transaction_date.desc()).all()

    # Check if any transactions were found
    if not transactions:
        return jsonify({'message': 'No transactions found for the specified date.'}), 404

    # Prepare the transaction data, including only the receiver's email, balance after transaction, and UUID
    transaction_list = [
        {
            'transaction_id': transaction.transaction_id,
            'receiver_email': transaction.recipient_email,
            'balance_after_transaction': transaction.balance_after_transaction
        }
        for transaction in transactions
    ]

    return jsonify({
        'message': 'Transaction history fetched successfully',
        'transactions': transaction_list
    }), 200


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