import base64
import functools
import os
import signal
import sys

from sql_interface import DB, PrimaryKey
from cache import Cache
from json_flask import JsonFlask

from flask import session, request, abort


# Set up SIGTERM handler
def sigterm_handler(signum, frame):
    print("Shutting down...")
    sys.exit(0)
signal.signal(signal.SIGTERM, sigterm_handler)


# Globals
db = DB("isometric", schema={
    "users": {
        "user_id": PrimaryKey,
        "user_name": str,
        "user_pwhash": bytes,
    }
})
db.validate_schema()
cache = Cache()


app = JsonFlask(__name__)
app.config.update(
    #SERVER_NAME="isometric.finance",
    SECRET_KEY=os.urandom(16),
    SESSION_COOKIE_NAME="isometric_session",
    APPLICATION_ROOT="/api/",
)


# Routes
@app.json_route('/register')
def register(username: str, password: str):
    print("JSON:", request.json)
    user_id = db.query_one("SELECT user_id FROM users WHERE user_name=%s", (username,))
    if user_id is not None:
        return {"status": "username is taken"}, 401
    user_token = "asdf"
    return {"status": "logged in", "token": user_token, "id": user_id}


@app.json_route('/login')
def login(username: str, password: str):
    print("JSON:", request.json)
    user_id = db.query_one("SELECT user_id FROM users WHERE user_name=%s AND user_pwhash=%s", (username, password.encode('utf-8')))
    if user_id is None:
        return {"status": "invalid credentials"}, 401
    user_token = "asdf"
    user_id = 5
    return {"status": "logged in", "token": user_token, "id": user_id}


# Start UWSGI server
if __name__ == '__main__':
    import waitress
    waitress.serve(app, host='0.0.0.0', port=80)