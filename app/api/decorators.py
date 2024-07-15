from flask import g, abort
from functools import wraps
from .errors import forbidden

# decorator to check permission or wraps function
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args,**kwargs):
            if not g.current_user.can(permission):
                return forbidden('Insuffiecient Permissions')
            return f(*args,**kwargs)
        return decorated_function
    return decorator