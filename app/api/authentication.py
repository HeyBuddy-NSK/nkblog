from flask_httpauth import HTTPBasicAuth
from . import api
basic_auth = HTTPBasicAuth()
from app.models import User
from flask import g, jsonify
from .errors import unauthorized, forbidden

# @basic_auth.verify_password
# def verify_password(email,password):
#     """
#     Verifies the password of user.
#     """
#     if email == '':
#         return False
    
#     user = User.query.filter_by(email = email).first()
#     if not user:
#         return False
#     g.current_user = user
    
#     return user.verify_password(password)

# new method using token for authentication.
@basic_auth.verify_password
def verify_password(email_or_token,password):
    """
    verifies the user.
    """
    if email_or_token == '':
        return False
    if password == '':
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True

        return g.current_user is not None
    
    # if email and password both are there.
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    
    g.current_user = user
    g.token_used = False
    return User.verify_password(password)

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
    
@api.route('/tokens/',methods=['GET','POST'])
def get_token():
    """
    To prevent users from bypassing the token expiration.
    """
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid Credentials')
    
    return jsonify({'token':g.current_user.generate_auth_token(expiration=3600), 'expiration':3600})