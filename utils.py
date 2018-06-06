import os
import os.path

from functools import wraps
from flask import request, Response


def read_env(fn='.env', dir=os.path.dirname(os.path.abspath(__file__))):
    """Read env file into environment, if found
    """
    envpath = os.path.join(dir, fn)
    env = {}
    if os.path.exists(envpath):
        with open(envpath, "r") as fh:
            for line in fh.readlines():
                if '#' not in line and '=' in line:
                    key, val = line.strip().split('=', 1)
                    env[key] = val
                    os.environ[key] = val
    return env


"""HTTP Basic Auth
from http://flask.pocoo.org/snippets/8/

Not used
"""

def check_auth(username, password):
    """This function is called to check if the login info is valid.
    """
    return password == 'password'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials',
        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
