from flask_httpauth import HTTPBasicAuth
from . import api
basic_auth = HTTPBasicAuth()
from app.models import User
from flask import g
from .errors import unauthorized

@basic_auth.verify_password
def verify_password(email,password):
    if email == '':
        return False
    
    user = User.query.filter_by(email = email).first()
    if not user:
        return False
    g.current_user = user
    
    return user.verify_password(password)

# HTTPauth error handler
from .errors import unauthorized
@basic_auth.error_handler
def auth_error():
    return unauthorized('Invalid Credentials')

@api.route('/posts/')
@basic_auth.login_required
def get_posts():
    pass