import psycopg2
from datetime import time, date, datetime, timedelta


PrimaryKey = object()


def ensure_connection(func):
    def _ensure_connection(self, *args, **kwargs):
        if self.connection is None:
            self.connect()
        try:
            return func(self, *args, **kwargs)
        except:
            self.connection = None
            raise
    return _ensure_connection


sql_type_conversions = {
    str: "text",
    int: "bigint",
    bytes: "bytea",
    bool: "boolean",
    float: "double precision",
    time: "time",
    date: "date",
    datetime: "timestamp",
    timedelta: "interval",
    PrimaryKey: "serial primary key",
}
python_type_conversions = {value: key for key, value in sql_type_conversions.items()}

def python_to_sql_type(name, python_type):
    return f"{name} {sql_type_conversions[python_type]}"

def sql_to_python_type(sql_type):
    return python_type_conversions[sql_type]


class DB:
    def __init__(self, dbname, schema=None):
        if schema is None:
            schema = {}
        self.dbname = dbname
        self.connection = None
        self.schema = schema

    def validate_schema(self):
        tables = self.query("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        for table, columns in self.schema.items():
            if table not in tables:
                self.execute(f'CREATE TABLE {table} ({", ".join(python_to_sql_type(name, python_type) for name, python_type in columns.items())});')

    def connect(self):
        # Close connection if it is open
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        # Open a new connection
        self.connection = psycopg2.connect(dbname=self.dbname)

    @ensure_connection
    def query(self, sql, params=None):
        with self.connection.cursor() as cursor:
            # Execute query
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            # Check what kind of results are ready
            if cursor.description is None:
                return None
            # Fetch results
            results = cursor.fetchall()
            if results is None:
                return None
            # For single column queries, return a flat list of items
            if len(cursor.description) == 1:
                return [result[0] for result in results]
            else:
                return results
    
    @ensure_connection
    def query_one(self, sql, params=None):
        with self.connection.cursor() as cursor:
            # Execute query
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            # Check what kind of results are ready
            if cursor.description is None:
                return None
            # Fetch results
            result = cursor.fetchone()
            if result is None:
                return None
            # For single column queries, return a single item
            if len(cursor.description) == 1:
                return result[0]
            else:
                return result

    @ensure_connection
    def execute(self, sql, params=None):
        results = self.query(sql, params)
        self.connection.commit()
        return results

    @ensure_connection
    def execute_one(self, sql, params=None):
        result = self.query_one(sql, params)
        self.connection.commit()
        return result