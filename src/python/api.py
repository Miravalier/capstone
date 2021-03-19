# Standard lib imports
import base64
import functools
import hashlib
import os
import secrets
import signal
import sys
from datetime import datetime, date
from enum import IntFlag
from hmac import compare_digest

# Pip dependency imports
from flask import session, request, abort

# Project imports
from sql_interface import DB, PrimaryKey, ForeignKey, Money
from json_flask import JsonFlask, UserId, DateStr


# Set up SIGTERM handler
def sigterm_handler(signum, frame):
    print("Shutting down...")
    sys.exit(0)
signal.signal(signal.SIGTERM, sigterm_handler)

# Permissions
class Permissions(IntFlag):
    NONE = 0
    VIEW = 1
    UPDATE = 2
    ADMIN = 4
    OWNER = 8

# Globals
db = DB("isometric", schema={
    "users": {
        "user_id": PrimaryKey,
        "user_name": str,
        "user_pw_hash": bytes,
        "user_pw_salt": bytes,
    },
    "budgets": {
        "budget_id": PrimaryKey,
        "budget_name": str,
    },
    "budget_permissions": {
        "budget_permission_id": PrimaryKey,
        "budget_id": ForeignKey("budgets", "budget_id"),
        "user_id": ForeignKey("users", "user_id"),
        "permissions": int,
    },
    "categories": {
        "category_id": PrimaryKey,
        "budget_id": ForeignKey("budgets", "budget_id"),
        "category_name": str,
    },
    "expenses": {
        "expense_id": PrimaryKey,
        "category_id": ForeignKey("categories", "category_id"),
        "expense_description": str,
        "expense_amount": Money,
        "expense_date": date,
        "entry_time": datetime
    },
})
db.validate_schema()


app = JsonFlask(__name__)
app.config.update(
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
    user_id = db.query_one("SELECT user_id FROM users WHERE user_name=%s;", (username,))
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
        "SELECT user_id, user_pw_hash, user_pw_salt FROM users WHERE user_name=%s;",
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


@app.json_route
def budget_create(user_id: UserId, budget_name: str):
    # Validate budget does not exist
    if db.query_one("SELECT budget_id FROM budgets WHERE budget_name=%s;", (budget_name,)):
        return {"error": "budget exists"}, 400
    # Create budget
    budget_id = db.execute_one(
        "INSERT INTO budgets (budget_name) VALUES (%s) RETURNING budget_id;",
        (budget_name,)
    )
    # Add owner permissions to creator
    db.execute("""
        INSERT INTO budget_permissions (budget_id, user_id, permissions)
        VALUES (%s, %s, %s);
    """, (budget_id, user_id, Permissions.OWNER))
    # Return status
    return {"status": "success", "id": budget_id}


@app.json_route
def budget_update(user_id: UserId, budget_id: int, budget_name: str):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.UPDATE:
        return {"error": "insufficient permissions"}, 403
    # Perform update
    db.execute("""
        UPDATE budgets SET budget_name=%s WHERE budget_id=%s;
    """, (budget_name, budget_id))
    # Return status
    return {"status": "success"}


@app.json_route
def budget_delete(user_id: UserId, budget_id: int):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Perform delete
    db.execute("""
        DELETE FROM budgets WHERE budget_id=%s;
    """, (budget_id,))
    # Return status
    return {"status": "success"}


@app.json_route
def category_create(user_id: UserId, budget_id: int, category_name: str):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.UPDATE:
        return {"error": "insufficient permissions"}, 403
    # Validate category does not exist
    category_id = db.query_one("""
        SELECT category_id FROM categories
        WHERE category_name=%s AND budget_id=%s;
    """, (category_name, budget_id))
    if category_id is not None:
        return {"error": "category exists"}, 400
    # Create category
    category_id = db.execute_one("""
        INSERT INTO categories (budget_id, category_name)
        VALUES (%s, %s) RETURNING category_id;
    """, (budget_id, category_name))
    # Return status
    return {"status": "success", "id": category_id}


@app.json_route
def category_update(user_id: UserId, budget_id: int,
        category_id: int, category_name: str):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.UPDATE:
        return {"error": "insufficient permissions"}, 403
    # Perform update
    db.execute("""
        UPDATE categories SET category_name=%s
        WHERE budget_id=%s AND category_id=%s;
    """, (category_name, budget_id, category_id))
    # Return status
    return {"status": "success"}


@app.json_route
def category_delete(user_id: UserId, budget_id: int, category_id: int):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Perform delete
    db.execute("""
        DELETE FROM categories WHERE budget_id=%s AND category_id=%s;
    """, (budget_id, category_id))
    # Return status
    return {"status": "success"}


@app.json_route
def expense_create(user_id: UserId, budget_id: int, category_id: int,
        description: str, expense_amount: Money, expense_date: DateStr):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.UPDATE:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    status = db.query_one("""
        SELECT category_id from categories
        WHERE category_id=%s AND budget_id=%s;
    """, (category_id, budget_id))
    if status is None:
        return {"error": "budget category does not exist"}, 400
    # Create expense
    expense_id = db.execute_one(
        """
            INSERT INTO expenses (
                category_id,
                expense_description, expense_amount, expense_date,
                entry_time
            )
            VALUES (%s, %s, %s, %s, %s) RETURNING expense_id;
        """,
        (
            category_id,
            description, expense_amount, expense_date,
            datetime.now()
        )
    )
    # Return stats
    return {"status": "success", "id": expense_id}


@app.json_route
def expense_update(user_id: UserId, budget_id: int,
        category_id: int, expense_id: int,
        description: str, expense_amount: Money, expense_date: DateStr):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.UPDATE:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    status = db.query_one("""
        SELECT category_id from categories
        WHERE category_id=%s AND budget_id=%s;
    """, (category_id, budget_id))
    if status is None:
        return {"error": "budget category does not exist"}, 400
    # Perform update
    db.execute(
        """
            UPDATE expenses
            SET expense_description=%s, expense_amount=%s, expense_date=%s
            WHERE category_id=%s AND expense_id=%s;
        """,
        (
            description, expense_amount, expense_date,
            category_id, expense_id
        )
    )
    # Return status
    return {"status": "success"}


@app.json_route
def expense_delete(user_id: UserId, budget_id: int,
        category_id: int, expense_id: int):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None or permissions < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    status = db.query_one("""
        SELECT category_id from categories
        WHERE category_id=%s AND budget_id=%s;
    """, (category_id, budget_id))
    if status is None:
        return {"error": "budget category does not exist"}, 400
    # Perform delete
    db.execute("""
        DELETE FROM expenses WHERE category_id=%s AND expense_id=%s;
    """, (category_id, expense_id))
    # Return status
    return {"status": "success"}


# Start UWSGI server
if __name__ == '__main__':
    import waitress
    waitress.serve(app, host='0.0.0.0', port=80)