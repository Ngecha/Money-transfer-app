from models import User, db
from flask import Flask
from flask_restful import Api, Resource
from flask_migrate import Migrate
from flask_cors import CORS
import os

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
# postgresql://moneytransferapp_user:7lX9VybTLSDTgeecUx9qN9anijeIcRci@dpg-cslqo6i3esus73c9jhv0-a.oregon-postgres.render.com/moneytransferapp

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.compact = False

migrate = Migrate(app, db)
db.init_app(app)
CORS(app)

api = Api(app)

class Users(Resource):
    def get(self):
        users = [user.to_dict() for user in User.query.all()]
        return users

api.add_resource(Users, '/users')


if __name__ == '__main__':
    app.run(debug=True, port=5555)
