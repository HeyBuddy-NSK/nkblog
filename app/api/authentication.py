from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()
from app.models import User
from flask import g

@auth.verify_password
def verify_password(email,password):
    if email == '':
        return False
    
    user = User.query.filter_by(email = email).first()
    if not user:
        return False
    g.current_user = user
    
    return user.verify_password(password)