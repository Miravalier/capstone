import psycopg2


def ensure_connection(func):
    def _ensure_connection(self, *args, **kwargs):
        if self.connection is None:
            self.connect()
        try:
            return func(*args, **kwargs)
        except:
            self.connection = None
            raise
    return _ensure_connection


class DB:
    def __init__(self, dbname):
        self.dbname = dbname
        self.connection = None

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
            # For single column queries, return a flat list of items
            if len(cursor.description) == 1:
                return (result[0] for result in results)
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