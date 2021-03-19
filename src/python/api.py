# Standard lib imports
import base64
import functools
import hashlib
import os
import secrets
import signal
import sys
from hmac import compare_digest

# Pip dependency imports
from flask import session, request, abort

# Project imports
from sql_interface import DB, PrimaryKey
from json_flask import JsonFlask, UserId


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
        "user_pw_hash": bytes,
        "user_pw_salt": bytes,
    }
})
db.validate_schema()


app = JsonFlask(__name__)
app.config.update(
    #SERVER_NAME="isometric.finance",
    SECRET_KEY=os.urandom(16),
    SESSION_COOKIE_NAME="isometric_session",
    APPLICATION_ROOT="/api/",
)


# Routes
@app.json_route
def register(username: str, password: str):
    print("JSON:", request.json)
    # Generate salt and hash password
    salt = secrets.token_bytes(16)
    password_hash = hashlib.scrypt(password.encode('utf-8'), salt=salt, r=16, n=4096, p=1)
    del password
    # Check if username is taken
    user_id = db.query_one("SELECT user_id FROM users WHERE user_name=%s", (username,))
    if user_id is not None:
        return {"error": "username is taken"}, 400
    # Create a new user in the DB
    user_id = db.execute_one(
        "INSERT INTO users (user_name, user_pw_hash, user_pw_salt) VALUES (%s, %s, %s) RETURNING user_id;",
        (username, password_hash, salt)
    )
    # Add user token to cache
    user_token = secrets.token_urlsafe(16)
    app.authtoken_cache[user_token] = user_id
    # Return token and id
    return {"status": "logged in", "token": user_token, "id": user_id}, 201


@app.json_route
def login(username: str, password: str):
    print("JSON:", request.json)
    # Lookup correct hash, salt, and id
    result = db.query_one(
        "SELECT user_id, user_pw_hash, user_pw_salt FROM users WHERE user_name=%s",
        (username,)
    )
    if result is None:
        return {"error": "invalid credentials"}, 401
    user_id, correct_hash, salt = result
    # Hash password
    given_hash = hashlib.scrypt(password.encode('utf-8'), salt=salt, r=16, n=4096, p=1)
    del password
    # Determine if the hashes match
    if not compare_digest(correct_hash, given_hash):
        return {"error": "invalid credentials"}, 401
    # Add user token to cache
    user_token = secrets.token_urlsafe(16)
    app.authtoken_cache[user_token] = user_id
    # Return token and id
    return {"status": "logged in", "token": user_token, "id": user_id}


@app.json_route
def status(user_id: UserId):
    return {"status": "logged in"}


# Start UWSGI server
if __name__ == '__main__':
    import waitress
    waitress.serve(app, host='0.0.0.0', port=80)