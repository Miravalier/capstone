import base64
import os
import signal
import sys
from sql_interface import DB

from flask import Flask, session, jsonify, request


# Wrap print() to log to stderr
_print = print
def print(*args, **kwargs):
    _print(*args, file=sys.stderr, **kwargs)


# Set up SIGTERM handler
def sigterm_handler(signum, frame):
    print("Shutting down...")
    sys.exit(0)
signal.signal(signal.SIGTERM, sigterm_handler)


# Globals
db = DB("isometric")

app = Flask(__name__)
app.config.update(
    #SERVER_NAME="isometric.finance",
    SECRET_KEY=os.urandom(16),
    SESSION_COOKIE_NAME="isometric_session",
    APPLICATION_ROOT="/api/",
)


# Routes
@app.route('/counter', methods=['GET'])
def counter():
    print("Counter")
    session['counter'] = session.get('counter', 0) + 1
    return jsonify({"potato": "lorem ipsum", "counter": session['counter']})


# Start UWSGI server
if __name__ == '__main__':
    import waitress
    waitress.serve(app, host='0.0.0.0', port=80)