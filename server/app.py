from flask import Flask, request, jsonify, session
from flask_login import LoginManager
from flask_migrate import Migrate
from functools import wraps
import bcrypt
from db import db
from flask_cors import CORS

from models import User, TransactionSummary, Analytics

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

#

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)