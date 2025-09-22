# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from psycopg import Connection, Cursor
from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager

class PoolObserver():
    def __init__(self, pool_manager: LRUConnectionPoolManager, *args, **kwargs):
        self.snapshot = []
        self.pool_manager = pool_manager

    def get_connection(self, dbname: str, persistent: bool = False):
        conn = self.pool_manager.get_connection(dbname, persistent)
        print(f"Getting connection to {dbname}")
        return ConnectionObserver(conn, self.snapshot)

class ConnectionObserver():
    def __init__(self, conn: Connection, snapshot: list):
        print(f"Initializing connection observer")
        self.snapshot = snapshot
        self.conn = conn

    def __enter__(self):
        print(f"Entering connection")
        return self.conn

    # def __exit__(self, exc_type, exc_value, traceback):
    #     self.conn.close()
    
    def cursor(self, *args, **kwargs):
        print(f"Getting cursor")
        return CursorObserver(self.conn.cursor(*args, **kwargs), self.snapshot)

class CursorObserver():
    def __init__(self, cursor: Cursor, snapshot: list):
        print(f"Initializing cursor observer")
        self.cursor = cursor
        self.snapshot = snapshot

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        self.cursor.close()

    def execute(self, query, *args, **kwargs):
        print(f"Executing {query}")
        self.snapshot.append(query)
        return self.cursor.execute(query, *args, **kwargs)

    def fetchone(self):
        result = self.cursor.fetchone()
        self.snapshot.append(result)
        return result

    def fetchall(self):
        result = self.cursor.fetchall()
        self.snapshot.append(result)
        return result
        
import types
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]
def test_snapshot(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    observer = PoolObserver(check.db_pool)

    def generate_new_connection(new_connection):
        print(f"Generating new connection function")
        def observed_new_connection(self,dbname):
            print(f"Getting new connection to {dbname}")
            conn = new_connection(dbname)
            print(f"New connection: {conn}")
            return ConnectionObserver(conn, observer.snapshot)
        return observed_new_connection
    check._new_connection = generate_new_connection(check._new_connection).__get__(check, check.__class__)
    check.db_pool = observer
    # conn = check._new_connection(check, "test")
    # with check.db() as conn:
    #     print(f"Got connection: {conn}")
    #     with conn.cursor() as cursor:
    #         cursor.execute("SELECT 1")
    check.run()
    assert observer.snapshot == ["SELECT 1"]