from models import User, Wallet
from flask import request, jsonify, session
from flask_cors import CORS

from app import app
from db import db

CORS(app)


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

    try:

        new_user = User(username=username, email=email, phone_number=phone_number, password=password, profile_image=profile_image)
        db.session.add(new_user)
        db.session.commit()

        new_wallet = Wallet(user_id=new_user.user_id, wallet_name="Default Wallet", balance=0.0)
        db.session.add(new_wallet)
        db.session.commit()

    except ValueError:
        return jsonify({"message": "Wrong phone number or email format"})

    return jsonify({
        "message": "User registered successfully!",
        "user": new_user.to_dict(),
        "wallet": new_wallet.to_dict()   
    }), 201


  
# User Login Route 
@app.route('/login', methods=['POST'])
def login():
        email = request.json.get("email")
        password = request.json.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.user_id
            session['username'] = user.username
            return jsonify({"token": "fake-jwt-token", "username": user.username})
        return {"error": "Invalid credentials"}, 401