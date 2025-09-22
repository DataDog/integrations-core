# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from psycopg import Connection, Cursor
from datadog_checks.postgres.connection_pool import LRUConnectionPoolManager
import contextlib
class PoolObserver():
    def __init__(self, pool_manager: LRUConnectionPoolManager, *args, **kwargs):
        self.snapshot = []
        self.pool_manager = pool_manager

    def get_connection(self, dbname: str, persistent: bool = False):
        conn = self.pool_manager.get_connection(dbname, persistent)
        print(f"Getting connection to {dbname}")
        return ConnectionObserver(conn, self.snapshot)
    
    def __getattr__(self, attr): 
        if attr not in self.__dict__: 
            print(f"Getting attribute {attr} from pool manager")
            return getattr(self.pool_manager, attr) 
        return super().__getattr__(attr) 

# Mark as contextmanagers because the underlying connection is a contextmanager
# @contextlib.contextmanager
class ConnectionObserver():
    def __init__(self, conn: Connection, snapshot: list):
        print(f"Initializing connection observer")
        self.snapshot = snapshot
        self.conn = conn

    @contextlib.contextmanager
    def cursor(self, *args, **kwargs):
        print(f"Getting cursor")
        yield CursorObserver(self.conn.cursor(*args, **kwargs), self.snapshot)

    def __getattr__(self, attr): 
        if attr not in self.__dict__: 
            print(f"Getting attribute {attr} from connection")
            return getattr(self.conn, attr) 
        return super().__getattr__(attr) 

# Mark as contextmanagers because the underlying cursor is a contextmanager
# @contextlib.contextmanager
class CursorObserver():
    def __init__(self, cursor: Cursor, snapshot: list):
        print(f"Initializing cursor observer {cursor}")
        self.cursor = cursor
        self.snapshot = snapshot

    def execute(self, query, *args, **kwargs):
        print(f"Executing {query}")
        self.snapshot.append(query)
        return self.cursor.execute(query, *args, **kwargs)

    def fetchone(self):
        print(f"Fetching one")
        result = self.cursor.fetchone()
        self.snapshot.append(result)
        return result

    def fetchall(self):
        print(f"Fetching all")
        result = self.cursor.fetchall()
        self.snapshot.append(result)
        return result

    def __getattr__(self, attr): 
        if attr not in self.__dict__: 
            print(f"Getting attribute {attr} from cursor")
            return getattr(self.cursor, attr) 
        return super().__getattr__(attr) 
    
        
import types
import inspect
pytestmark = [pytest.mark.usefixtures('dd_environment')]
def test_snapshot(aggregator, integration_check, pg_instance):
    check = integration_check(pg_instance)
    observer = PoolObserver(check.db_pool)

    def generate_new_connection(new_connection):
        def observed_new_connection(dbname):
            print(f"Getting new connection to {dbname}")
            try:
                conn = new_connection(dbname)
            except Exception as e:
                print(f"Error getting new connection: {e}")
                raise e
            print(f"New connection: {conn}")
            return ConnectionObserver(conn, observer.snapshot)
        return observed_new_connection
    check._new_connection = generate_new_connection(check._new_connection)
    check.db_pool = observer
    # conn = check._new_connection(check, "test")
    # with check.db() as conn:
    #     print(f"Got connection: {conn}")
    #     with conn.cursor() as cursor:
    #         cursor.execute("SELECT 1")
    check.run()
    assert observer.snapshot == ["SELECT 1"]