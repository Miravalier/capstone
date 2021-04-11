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
from typing import Optional

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
        "previous_budget_id": int,
        "next_budget_id": int,
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


# Database Functions
def budget_permissions(budget_id: int, user_id: int):
    # Validate permissions
    permissions = db.query_one("""
        SELECT permissions FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    if permissions is None:
        return Permissions.NONE
    else:
        return permissions


def category_in_budget(category_id: int, budget_id: int):
    category_id = db.query_one("""
        SELECT category_id from categories
        WHERE category_id=%s AND budget_id=%s;
    """, (category_id, budget_id))
    return category_id is not None


def is_valid_user_id(user_id: int):
    user_id = db.query_one("""
        SELECT user_id FROM users
        WHERE user_id=%s;
    """, (user_id,))
    return user_id is not None


# Routes
@app.json_route
def register(username: str, password: str):
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
    return {"status": "success", "authtoken": user_token, "id": user_id}, 201


@app.json_route
def login(username: str, password: str):
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
    return {"status": "success", "authtoken": user_token, "id": user_id}


@app.json_route
def status(user_id: UserId):
    return {"status": "success"}


@app.json_route
def budget_permissions_set(user_id: UserId, budget_id: int,
        recipient_user_id: int, permissions: int):
    # Lookup permissions
    user_permissions = budget_permissions(budget_id, user_id)
    recipient_permissions = budget_permissions(budget_id, recipient_user_id)
    # Verify that the user is at least an admin
    if user_permissions < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Verify the recipient is a real user
    if not is_valid_user_id(recipient_user_id):
        return {"error": "user does not exist"}, 400
    # Validate the recipients permissions are lower than the user's own
    if recipient_permissions >= user_permissions:
        return {"error": "insufficient permissions"}, 403
    # Validate the permissions being set are lower than the user's own
    if permissions >= user_permissions:
        return {"error": "insufficient permissions"}, 403
    # Set the permissions
    if permissions == Permissions.NONE:
        db.execute("""
            DELETE FROM budget_permissions
            WHERE budget_id=%s AND user_id=%s;
        """, (budget_id, recipient_user_id))
    else:
        if recipient_permissions == Permissions.NONE:
            db.execute("""
                INSERT INTO budget_permissions
                (budget_id, user_id, permissions)
                VALUES (%s, %s, %s);
            """, (budget_id, recipient_user_id, permissions))
        else:
            db.execute("""
                UPDATE budget_permissions SET permissions=%s
                WHERE budget_id=%s AND user_id=%s;
            """, (permissions, budget_id, recipient_user_id))
    # Return status
    return {"status": "success"}


@app.json_route
def budget_permissions_get(auth_user_id: UserId, budget_id: int,
        user_id: int):
    # Lookup permissions
    user_permissions = budget_permissions(budget_id, auth_user_id)
    recipient_permissions = budget_permissions(budget_id, user_id)
    # Verify the user is an admin on this budget
    if user_permissions < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Verify the recipient is a real user
    if not is_valid_user_id(user_id):
        return {"error": "user does not exist"}, 400
    # Return status
    return {"status": "success", "permissions": recipient_permissions}


@app.json_route
def budget_permissions_transfer(user_id: UserId, budget_id: int,
        recipient_user_id: int):
    # Verify user is the owner of the budget
    if budget_permissions(budget_id, user_id) != Permissions.OWNER:
        return {"error": "insufficient permissions"}, 403
    # Verify the recipient is a real user
    if not is_valid_user_id(recipient_user_id):
        return {"error": "user does not exist"}, 400
    # Remove owner privileges from the owner
    db.execute("""
        UPDATE budget_permissions SET permissions=%s
        WHERE budget_id=%s AND user_id=%s;
    """, (Permissions.ADMIN, budget_id, user_id))
    # Grant owner privileges to the recipient
    if budget_permissions(budget_id, recipient_user_id) == Permissions.NONE:
        db.execute("""
            INSERT INTO budget_permissions
            (budget_id, user_id, permissions)
            VALUES (%s, %s, %s);
        """, (budget_id, recipient_user_id, Permissions.OWNER))
    else:
        db.execute("""
            UPDATE budget_permissions SET permissions=%s
            WHERE budget_id=%s AND user_id=%s;
        """, (Permissions.OWNER, budget_id, recipient_user_id))
    # Return status
    return {"status": "success"}


@app.json_route
def budget_permissions_relinquish(user_id: UserId, budget_id: int):
    # Get user permissions
    permissions = budget_permissions(budget_id, user_id)
    # Verify user is not the owner of the budget
    if permissions == Permissions.OWNER:
        return {"error": "owner cannot relinquish"}, 400
    # Verify the user has any permissions to relinquish
    if permissions == Permissions.NONE:
        return {"error": "no permissions to relinquish"}, 400
    # Relinquish permissions
    db.execute("""
        DELETE FROM budget_permissions
        WHERE budget_id=%s AND user_id=%s;
    """, (budget_id, user_id))
    # Return status
    return {"status": "success"}



@app.json_route
def budget_create(user_id: UserId, budget_name: str,
        previous_budget_id: Optional[int]):
    # Validate budget does not exist
    budget_id = db.query_one("""
        SELECT budget_id FROM budgets WHERE budget_name=%s;
    """, (budget_name,))
    if budget_id is not None:
        return {"error": "budget exists"}, 400
    # If previous budget, validate that budget has no child
    if previous_budget_id:
        existing_child_id = db.query_one("""
            SELECT budget_id FROM budgets WHERE previous_budget_id=%s;
        """, (previous_budget_id,))
        if existing_child_id is not None:
            return {"error": "parent budget has a child already"}, 400
        
    # Create budget
    budget_id = db.execute_one(
        "INSERT INTO budgets (budget_name, previous_budget_id) VALUES (%s, %s) RETURNING budget_id;",
        (budget_name, previous_budget_id)
    )
    # Add next_budget_id to previous budget
    db.execute("""
        UPDATE budgets SET next_budget_id=%s
        WHERE budget_id=%s;
    """, (budget_id, previous_budget_id))
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
    if budget_permissions(budget_id, user_id) < Permissions.UPDATE:
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
    if budget_permissions(budget_id, user_id) < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Perform delete
    db.execute("""
        DELETE FROM budgets WHERE budget_id=%s;
    """, (budget_id,))
    # Return status
    return {"status": "success"}


@app.json_route
def budget_list(user_id: UserId):
    # Get list of budgets
    budgets = db.query("""
        SELECT  budgets.budget_id, budgets.budget_name,
                budgets.previous_budget_id, budgets.next_budget_id,
                budget_permissions.permissions
        FROM budgets JOIN budget_permissions
        ON budgets.budget_id=budget_permissions.budget_id
        WHERE budget_permissions.user_id=%s
        ORDER BY budgets.budget_id;
    """, (user_id,))
    # Convert tuples in array to dictionaries
    budgets = [
        {
            "id": budget_id,
            "previous_id": previous_id,
            "next_id": next_id,
            "name": name,
            "permissions": permissions
        } for budget_id, name, previous_id, next_id, permissions in budgets
    ]
    # Return budgets
    return {"status": "success", "budgets": budgets}


@app.json_route
def budget_info(user_id: UserId, budget_id: int):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.VIEW:
        return {"error": "insufficient permissions"}, 403
    # Get info
    info = db.query_one(
        """
            SELECT budget_name, previous_budget_id,
                next_budget_id, permissions
            FROM budgets JOIN budget_permissions
            ON budgets.budget_id=budget_permissions.budget_id
            WHERE budgets.budget_id=%s AND budget_permissions.user_id=%s
        """,
        (budget_id, user_id)
    )
    if info is None:
        return {"error": "budget does not exist"}, 400
    name, previous_id, next_id, permissions = info
    # Return info
    return {
        "status": "success", "name": name, "permissions": permissions,
        "previous_id": previous_id, "next_id": next_id
    }


@app.json_route
def category_create(user_id: UserId, budget_id: int, category_name: str):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.UPDATE:
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
    if budget_permissions(budget_id, user_id) < Permissions.UPDATE:
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
    if budget_permissions(budget_id, user_id) < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Perform delete
    db.execute("""
        DELETE FROM categories WHERE budget_id=%s AND category_id=%s;
    """, (budget_id, category_id))
    # Return status
    return {"status": "success"}


@app.json_route
def category_list(user_id: UserId, budget_id: int):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.VIEW:
        return {"error": "insufficient permissions"}, 403
    # Query for categories
    categories = db.query("""
        SELECT category_id, category_name
        FROM categories WHERE budget_id=%s
        ORDER BY category_id;
    """, (budget_id,))
    # Transform tuples into dictionaries
    categories = [
        {
            "id": category_id,
            "name": category_name,
        } for category_id, category_name in categories
    ]
    # Return categories
    return {"status": "success", "categories": categories}


@app.json_route
def category_info(user_id: UserId, budget_id: int, category_id: int):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.VIEW:
        return {"error": "insufficient permissions"}, 403
    # Get category info
    name = db.query_one("""
        SELECT category_name FROM categories
        WHERE budget_id=%s AND category_id=%s;
    """, (budget_id, category_id))
    if name is None:
        return {"error": "category does not exist"}, 400
    # Return info
    return {"status": "success", "name": name}


@app.json_route
def expense_create(user_id: UserId, budget_id: int, category_id: int,
        description: str, expense_amount: Money, expense_date: DateStr):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.UPDATE:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    if not category_in_budget(category_id, budget_id):
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
    if budget_permissions(budget_id, user_id) < Permissions.UPDATE:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    if not category_in_budget(category_id, budget_id):
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
    return {
        "status": "success",
        "description": description,
        "amount": f"${expense_amount:.2f}",
        "date": expense_date.isoformat()
    }


@app.json_route
def expense_delete(user_id: UserId, budget_id: int,
        category_id: int, expense_id: int):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.ADMIN:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    if not category_in_budget(category_id, budget_id):
        return {"error": "budget category does not exist"}, 400
    # Perform delete
    db.execute("""
        DELETE FROM expenses WHERE category_id=%s AND expense_id=%s;
    """, (category_id, expense_id))
    # Return status
    return {"status": "success"}


@app.json_route
def expense_info(user_id: UserId, budget_id: int, category_id: int,
        expense_id: int):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.VIEW:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    if not category_in_budget(category_id, budget_id):
        return {"error": "budget category does not exist"}, 400
    # Get info
    info = db.query_one("""
        SELECT expense_description, expense_amount, expense_date
        FROM expenses WHERE expense_id=%s AND category_id=%s;
    """, (expense_id, category_id))
    if info is None:
        return {"error": "expense does not exist"}, 400
    description, amount, date = info
    # Return status
    return {
        "status": "success",
        "description": description,
        "amount": str(amount),
        "date": date.isoformat()
    }


@app.json_route
def expense_list(user_id: UserId, budget_id: int, category_id: int):
    # Validate permissions
    if budget_permissions(budget_id, user_id) < Permissions.VIEW:
        return {"error": "insufficient permissions"}, 403
    # Validate the given category belongs to the given budget
    if not category_in_budget(category_id, budget_id):
        return {"error": "budget category does not exist"}, 400
    # Query for expenses
    expenses = db.query("""
        SELECT  expense_id, expense_description, expense_amount,
                expense_date
        FROM expenses WHERE category_id=%s
        ORDER BY expense_date, expense_id;
    """, (category_id,))
    # Transform tuples into dictionaries
    expenses = [
        {
            "id": expense_id,
            "description": expense_description,
            "amount": str(expense_amount),
            "date": expense_date.isoformat()
        } for expense_id, expense_description, \
            expense_amount, expense_date in expenses
    ]
    # Return expenses
    return {"status": "success", "expenses": expenses}


# Start UWSGI server
if __name__ == '__main__':
    import waitress
    waitress.serve(app, host='0.0.0.0', port=80)