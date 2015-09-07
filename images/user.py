
import logging, functools
from bottle import Bottle, auth_basic, request, HTTPError
from enum import IntEnum, unique
from .types import PropertySet, Property, strip
from .database import get_db, password_hash
from . import api, User


BASE = '/user'
app = Bottle()
api.register(BASE, app)


def authenticate(username, password):
    """
    Bottle-compatible simple-checker that stores the user descriptor
    of the currently logged in user onto the request.
    """
    with get_db().transaction() as t:
        try:
            user = (t.query(User)
                     .filter(User.name==username and User.password==password_hash(password))
                     .one())

            request.user = UserDescriptor(
                id=user.id,
                status=User.Status(user.status),
                name=user.name,
                fullname=user.fullname,
                user_class=User.Class(user.user_class)
            )
            return True
        except:
            return False


@app.get('/me')
@auth_basic(authenticate)
def me():
    json = request.user.to_json()
    logging.info("Me\n%s", json)
    return json


class UserDescriptor(PropertySet):
    id = Property(int)
    status = Property(enum=User.Status)
    name = Property()
    fullname = Property()
    user_class = Property(enum=User.Class)


def current_user_id():
    """
    Shorthand for retrieving the currently logged in user, if any.
    """
    try:
        return request.user.id
    except AttributeError:
        return None


def require_admin(realm="private"):
    """
    Bottle Callback decorator to require the current
    user to be admin or through a permission denied
    """
    def decorator(func):

        @functools.wraps(func)
        def wrapper(*a, **ka):
            if request.user.user_class != User.Class.admin:
                err = HTTPError(401, "Admin permission required")
                err.add_header('WWW-Authenticate', 'Basic realm="%s"' % realm)
                return err
            return func(*a, **ka)

        return wrapper

    return decorator


def no_guests():
    """
    Bottle Callback decorator to require the current
    user to be of higher class than guest
    """

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*a, **ka):
            if request.user.user_class is User.Class.guest:
                err = HTTPError(401, "Guests not allowed")
                return err
            return func(*a, **ka)

        return wrapper

    return decorator


def current_is_user():
    return request.user.user_class is not User.Class.guest 


def require_user_id(user_id):
    """
    Shorthand for requiring a certain user or raise a 401
    """
    if user_id != request.user.id:
        raise HTTPError(401, "Access denied")
