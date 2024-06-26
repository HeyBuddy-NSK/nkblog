from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager
from flask import current_app as app
from flask_login import UserMixin, AnonymousUserMixin
import jwt
from time import time

# Class to set permissions
class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16

class AnonymousUser(AnonymousUserMixin):
    def can(self,permissions):
        return False
    
    def is_administrator(self):
        return False
    
login_manager.anonymous_user = AnonymousUser

# Class for Role database.
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean,default=False,index=True)
    permission = db.Column(db.Integer)
    users = db.relationship('User', backref='role')

    def __init__(self,**kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permission is None:
            self.permission = 0

    def __repr__(self):
        return '<Role %r>' % self.name
    
    # function to add permissions
    def add_permission(self,perm):
        if not self.has_permission(perm):
            self.permission = perm

    # function to reset permissions
    def reset_permission(self):
        self.permission = 0
    
    # function to check if permission is there or not
    def has_permission(self,perm):
        return self.permission & perm == perm
    
    @staticmethod
    def insert_roles():
        roles = {
            'User':[Permission.FOLLOW,Permission.WRITE,Permission.COMMENT],
            'Moderator':[Permission.FOLLOW,Permission.WRITE,Permission.COMMENT,Permission.MODERATE],
            'Administrator':[Permission.FOLLOW,Permission.WRITE,Permission.COMMENT,Permission.MODERATE,Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)

            role.reset_permission()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name==default_role)
            db.session.add(role)

        db.session.commit()


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
    
    # const
    def __init__(self,**kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email == app.config['NKBLOG_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()

            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    def can(self,perm):
        return self.role is not None and self.role.has_permission(perm)
    
    def is_administrator(self):
        return self.can(Permission.ADMIN)

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