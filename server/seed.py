from app import app, db
from models import User
from faker import Faker

with app.app_context():
    faker=Faker()
    
    User.query.delete()
        
    users=[]
    
    for n in range(1):
        username = faker.name()
        user = User(username = username)
        users.append(user)
    db.session.add_all(users)
    db.session.commit()