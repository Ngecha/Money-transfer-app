from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import db

#create app
app= Flask(__name__)

#initialize extentions with the app
db.init_app(app)

#database configurations

