from flask import Flask
from flask_migrate import Migrate
import os
from db import db  
from models import User, Wallet, Beneficiary, Transaction  # Import models

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False

# Initialize db and Flask-Migrate
db.init_app(app)
migrate = Migrate(app, db)

if __name__ == "__main__":
    app.run(debug=True)
