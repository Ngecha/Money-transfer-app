from models import User, Wallet, Transaction, Beneficiary, TransactionSummary, Analytics### USER AUTHENTICATION ROUTES ###
from flask import Flask, request, jsonify, redirect, url_for, session,make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
from flask_login import UserMixin
from functools import wraps


from app import app
from db import db



### WALLET ROUTES ###
# Create a Wallet
@app.route('/wallet', methods=['POST'])
def create_wallet():
    data = request.json
    user_id=data.get("user_id")
    wallet_name = data.get('wallet_name', 'My Wallet')
    new_wallet = Wallet(user_id=user_id, wallet_name=wallet_name)
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