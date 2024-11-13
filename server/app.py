from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from db import db
from models import User, Wallet, Transaction, Beneficiary, TransactionSummary, Analytics

# Create app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To disable modification tracking, which can be performance-heavy

# Initialize extensions with the app
db.init_app(app)
migrate = Migrate(app, db)

# Import routes after initializing app
from routes import register_routes
register_routes(app)

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
