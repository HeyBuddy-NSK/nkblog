from flask_httpauth import HTTPBasicAuth
from . import api
basic_auth = HTTPBasicAuth()
from app.models import User
from flask import g
from .errors import unauthorized, forbidden

@basic_auth.verify_password
def verify_password(email,password):
    """
    Verifies the password of user.
    """
    if email == '':
        return False
    
    user = User.query.filter_by(email = email).first()
    if not user:
        return False
    g.current_user = user
    
    return user.verify_password(password)

# HTTPauth error handler
@basic_auth.error_handler
def auth_error():
    """
    Handles the authentication error.
    """
    return unauthorized('Invalid Credentials')

@api.route('/posts/')
@basic_auth.login_required
def get_posts():
    """
    Get posts from the database.
    """
    pass

@api.before_request
@basic_auth.login_required
def before_request():
    """
    Authentication will be done automatically for all the routes in bluprint.
    Also it reject authorized user who have not confirmed their account.
    """
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden('unconfirmed account.')