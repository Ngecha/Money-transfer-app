from models import User, Wallet, Transaction
from flask import request, jsonify, session
from sqlalchemy.exc import SQLAlchemyError


from app import app
from db import db


def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

### TRANSACTION ROUTES ###

@app.route('/transaction', methods=['POST'])
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
        transaction_fee = 20
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

    current_user_id = session['user_id']
    current_user = User.query.get(current_user_id)
    transaction = Transaction.query.get(transaction_id)

    if not transaction:
        return jsonify({"error": "Transaction not found!"}), 404

    if transaction.is_reversed:
        return jsonify({"error": "Transaction has already been reversed!"}), 400

    if transaction.user_id != current_user.user_id:
        return jsonify({"error": "You cannot reverse a transaction that you did not initiate!"}), 403

    sender_wallet = Wallet.query.get(transaction.sender_wallet_id)
    receiver_wallet = Wallet.query.get(transaction.receiver_wallet_id)

    if not sender_wallet or not receiver_wallet:
        return jsonify({"error": "Invalid wallet IDs associated with this transaction!"}), 400

    if receiver_wallet.balance < transaction.amount:
        return jsonify({"error": "Receiver does not have sufficient funds for reversal!"}), 400

    try:
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