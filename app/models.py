from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager
from flask import current_app as app
from flask_login import UserMixin
import jwt
from time import time

# Class for Role database.
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role')

    def __repr__(self):
        return '<Role %r>' % self.name

# Class for User database.
class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(64),unique=True,index=True)
    username = db.Column(db.String(64),unique=True, index=True)
    role_id = db.Column(db.Integer,db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)

    # authentication password
    password_hash = db.Column(db.String(128))
    

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')
    
    @password.setter
    def password(self,password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username
    
    def generate_confirmation_token(self, exp_time=3600):
        token = jwt.encode({'confirm':self.id, 'exp': time()+exp_time},app.config['SECRET_KEY'],algorithm='HS256')
        
        return token
    
    def confirm(self, token):
        try:
            data = jwt.decode(token,app.config['SECRET_KEY'],
                              algorithms='HS256')['confirm']
            
        except:
            return False
        self.confirmed = True
        db.session.add(self)
        return True
 

# Function to load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))