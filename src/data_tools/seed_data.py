#!/usr/bin/env python3
import hashlib
import json
import psycopg2
import random
import secrets
from datetime import datetime, date
from decimal import Decimal

seed_data = {}
connection = None


# Functions
def startup():
    global connection
    global seed_data
    connection = psycopg2.connect(dbname="isometric")
    with open("data/seed_data.json") as f:
        seed_data = json.load(f)


def main():
    today = date.today()
    now = datetime.now()

    # Creds are admin/password
    username = "admin"
    password = b"password"
    # Generate salt and hash password
    salt = secrets.token_bytes(16)
    password_hash = hashlib.scrypt(password, salt=salt, r=16, n=4096, p=1)
    # Create a new user in the DB
    user_id = query(
        "INSERT INTO users (user_name, user_pw_hash, user_pw_salt) VALUES (%s, %s, %s) RETURNING user_id;",
        (username, password_hash, salt)
    )

    # Insert budgets
    yearly_total = seed_data['total']
    budget_names = ('Q1 2021', 'Q2 2021', 'Q3 2021', 'Q4 2021')
    for i, budget_name in enumerate(budget_names):
        budget_total = yearly_total/4
        # First budget
        if i == 0:
            budget_id = query("INSERT INTO budgets(budget_name) VALUES (%s) RETURNING budget_id;",
                    (budget_name,))
        # Other budgets
        else:
            budget_id = query(
                """
                    INSERT INTO budgets(budget_name, previous_budget_id)
                    VALUES (%s, %s)
                    RETURNING budget_id;
                """,
                (budget_name, previous_budget_id)
            )
            execute("UPDATE budgets SET next_budget_id=%s WHERE budget_id=%s",
                    (budget_id, previous_budget_id))

        # Insert budget permissions
        execute(
            """
                INSERT INTO budget_permissions(budget_id, user_id, permissions)
                VALUES (%s, %s, %s);
            """,
            (budget_id, user_id, 8) # 8 is OWNER
        )

        # Insert categories
        for category, percent in seed_data['percentages'].items():
            category_id = query(
                """
                    INSERT INTO categories(budget_id, category_name) VALUES (%s, %s)
                    RETURNING category_id;
                """,
                (budget_id, category)
            )

            # Insert expenses
            category_total = budget_total * (percent/100)
            expenses = seed_data['items'][category]
            multiplier = 1
            for expense in expenses:
                multiplier *= 0.9
                expense_id = query(
                    """
                        INSERT INTO expenses(category_id, expense_description, expense_amount,
                                            expense_date, entry_time)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING expense_id;
                    """,
                    (
                        category_id,
                        expense,
                        Decimal(approximate(category_total / len(expenses)) * multiplier),
                        today,
                        now
                    )
                )

        # Update previous budget id for next time
        previous_budget_id = budget_id



def cleanup():
    connection.commit()
    connection.close()


def approximate(value):
    off_by = value / 10
    lower_bound = int(value - off_by)
    upper_bound = int(value + off_by)
    return random.randrange(lower_bound, upper_bound+1) + (random.randrange(1,100)/100)


def query(cmd, args=None):
    with connection.cursor() as cursor:
        if args:
            cursor.execute(cmd, args)
        else:
            cursor.execute(cmd)
        return cursor.fetchone()[0]


def execute(cmd, args=None):
    with connection.cursor() as cursor:
        if args:
            cursor.execute(cmd, args)
        else:
            cursor.execute(cmd)


if __name__ == '__main__':
    startup()
    main()
    cleanup()
    print("Data seeded!")
