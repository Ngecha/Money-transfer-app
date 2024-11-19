from models import User, Wallet
from flask import request, jsonify,session
from flask_cors import CORS


from app import app
from db import db

CORS(app)


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

@app.route("/users", methods=['GET'])
def get_users():
    try:
        # Query all users
        users = User.query.all()

        # Serialize the users
        users_list = [user.to_dict() for user in users]

        # Construct response
        response = {
            "users": users_list,
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
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return {"message": "Logged out successfully"}, 200