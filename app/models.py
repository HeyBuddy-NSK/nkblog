from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager
from flask import current_app as app
from flask_login import UserMixin, AnonymousUserMixin
import jwt
from time import time
import datetime
from flask import request, url_for
import hashlib
from markdown import markdown
import bleach
from app.exceptions import ValidationError

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
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self,**kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permission is None:
            self.permission = 0

    def __repr__(self):
        return '<Role %r>' % self.name
    
    # function to add permissions
    def add_permission(self,perm):
        if not self.has_permission(perm):
            self.permission += perm

    # remove permissions
    def remove_permission(self,perm):
        if self.has_permission(perm):
            self.permission -= perm

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

# creating table to save follow information.
class Follow(db.Model):
    __tablename__='follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))

# Class for User database.
class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(64),unique=True,index=True)
    username = db.Column(db.String(64),unique=True, index=True)
    role_id = db.Column(db.Integer,db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)
    avatar_hash = db.Column(db.String(32))

    # info about user
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(),default=datetime.datetime.now(datetime.timezone.utc))
    last_seen = db.Column(db.DateTime(),default=datetime.datetime.now(datetime.timezone.utc))

    # to store posts data
    posts = db.relationship('Post',backref='author',lazy='dynamic')

    # creating new relationship for followers and followed.
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower',lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed',lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    
    # relationship for comments
    comments = db.relationship('Comment',backref='author',lazy='dynamic')

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
                # print(self.role)
                # print('role set successfully.')
        
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()

        # making users their own follower
        # self.follow(self)

    # methods to manage follower and followed.
    def follow(self,user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        
        return self.followed.filter_by(followed_id=user.id).first() is not None
    
    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id).first() is not None
    
    # making users their own follower
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()


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

    # function declared as a property to perform logic for getting only followed users posts.
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id==Post.author_id).filter(Follow.follower_id==self.id)

    def verify_password(self,password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username
    
    def generate_confirmation_token(self, exp_time=3600):
        token = jwt.encode({'confirm':self.id, 'exp': time()+exp_time},app.config['SECRET_KEY'],algorithm='HS256')
        
        return token
    
    # method to confirm account
    def confirm(self, token):
        try:
            data = jwt.decode(token,app.config['SECRET_KEY'],
                              algorithms='HS256')['confirm']
            
        except:
            return False
        
        if data.get('confirm') != self.id:
            return False
        
        self.confirmed = True
        db.session.add(self)
        return True
    
    # method to update last seen
    def ping(self):
        self.last_seen = datetime.datetime.now(datetime.timezone.utc)
        db.session.add(self)
        db.session.commit()

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    # function to create avatar for user by using email
    def gravatar(self,size=100,default='identicon',rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.gravatar_hash() or self.avatar_hash
        avatar_url = f"{url}/{hash}?s={size}&d={default}&r={rating}"
        # print(avatar_url)
        return avatar_url
    
    # method to generate authentication token
    def generate_auth_token(self,expiration):
        auth_token = jwt.encode({'id':self.id, 'exp': time()+expiration},app.config['SECRET_KEY'],algorithm='HS256')
        return auth_token
    
    # method to verify authentication token
    @staticmethod
    def verify_auth_token(auth_token):
        try:
            data = jwt.decode(auth_token,app.config['SECRET_KEY'],algorithms='HS256')['id']
        except:
            return None
        
        return User.query.get(data)
    
    def to_json(self):
        """
        Converts user to json format.
        """
        json_user = {
            'url':url_for('api.get_user',id=self.id),
            'username':self.username,
            'member_since':self.member_since,
            'last_seen':self.last_seen,
            'posts_url':url_for('api.get_user_posts',id=self.id),
            'followed_posts_url':url_for('api.get_user_followed_posts',id=self.id),
            'post_count':self.posts.count()
        }

        return json_user


# db table to store posts data.
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.now(datetime.timezone.utc))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # relationship for comments
    comments = db.relationship('Comment',backref='post',lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a','abbr','acronym','b','blockquote','code',
                        'em','i','li','ol','pre','strong','ul','h1','h2',
                        'h3']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value,output_format='html'),
            tags=allowed_tags, strip=True
        ))

    def to_json(self):
        """
        converts post to json format.
        """
        json_post = {
            'url':url_for('api.get_post',id=self.id),
            'body':self.body,
            'body_html':self.body_html,
            'timestamp':self.timestamp,
            'author_url':url_for('api.get_user',id=self.author_id),
            'comments_url':url_for('api.get_post_comments',id=self.id),
            'comment_count':self.comments.count()
        }

        return json_post
    
    # method to convert json back to post or original
    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('Post does not have a boddy.')
        
        return Post(body=body)

db.event.listen(Post.body,'set',Post.on_changed_body)

# db table model to store comments made by user.
class Comment(db.Model):
    __tablename__='comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime,index=True, default=datetime.datetime.now(datetime.timezone.utc))
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a','abbr','acronym','b','code','em','i','strong']

        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True
        ))

db.event.listen(Comment.body, 'set', Comment.on_changed_body)
    
# Function to load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))