# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import time
import datetime

import psycopg2

from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool


def test_conn_pool(pg_instance):
    """
    Test simple case of creating a connection pool, pruning a stale connection,
    and closing all connections.
    """
    check = PostgreSql('postgres', {}, [pg_instance])

    pool = MultiDatabaseConnectionPool(check._new_connection)
    db = pool.get_connection('postgres', 1)
    pool.prune_connections()
    assert len(pool._conns) == 1

    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute("select 1")
        rows = cursor.fetchall()
        assert len(rows) == 1 and rows[0][0] == 1

    time.sleep(0.001)
    pool.prune_connections()
    assert len(pool._conns) == 0

    db = pool.get_connection('postgres', 999*1000)
    assert len(pool._conns) == 1
    success = pool.close_all_connections()
    assert success
    assert len(pool._conns) == 0


def test_conn_pool_no_leaks(pg_instance):
    """
    Test a scenario where many connections are created. These connections should be open on the database
    then should properly close on the pooler side and database when pruned and/or closed.
    """
    check = PostgreSql('postgres', {}, [pg_instance])

    pool = MultiDatabaseConnectionPool(check._new_connection)
    ttl_long = 90*1000
    ttl_short = 1

    def get_time():
        with pool.get_connection('postgres', 1).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT now()")
            return cursor.fetchone()

    def get_activity():
        with pool.get_connection('postgres', 1).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT datname, usename, state FROM pg_stat_activity WHERE usename = 'datadog' AND datname != 'postgres' AND query_start > %s", start_time)
            return cursor.fetchall()

    def get_many_connections(count, ttl):
        for i in range(0, count):
            dbname = 'dogs_{}'.format(i)
            db = pool.get_connection(dbname, ttl)
            with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute("select current_database()")
                rows = cursor.fetchall()
                assert len(rows) == 1 and rows[0][0] == dbname

    try:
        start_time = get_time()
        pool.close_all_connections()

        # Create many connections with long-lived TTLs
        get_many_connections(50, ttl_long)
        assert len(pool._conns) == 50
        # Ensure those connections have the correct deadline and connection status
        for i in range(0, 50):
            dbname = 'dogs_{}'.format(i)
            db, deadline = pool._conns[dbname]
            approximate_deadline = datetime.datetime.now() + datetime.timedelta(milliseconds=ttl_long)
            assert approximate_deadline - datetime.timedelta(seconds=1) < deadline < approximate_deadline + datetime.timedelta(seconds=1)
            assert not db.closed
            assert db.status == psycopg2.extensions.STATUS_READY
        # Check that those pooled connections do exist on the database
        rows = get_activity()
        assert len(rows) == 50
        assert len(set(row['datname'] for row in rows)) == 50
        assert all(row['state'] == 'idle' for row in rows)

        # Repeat this process many times and expect that only one connection is created per database
        for i in range(100):
            get_many_connections(50, ttl_long)

        time.sleep(2)  # postgres needs some time to terminate PIDs for closed connections
        rows = get_activity()
        assert len(rows) == 50, 'Leaked connections!'
        assert len(set(row['datname'] for row in rows)) == 50
        assert all(row['state'] == 'idle' for row in rows)
        
        # Now update db connections with short-lived TTLs and expect them to self-prune
        # TODO

    finally:
        success = pool.close_all_connections()
        print('Successfully closed all connections? {}'.format(success))
        assert success
        assert len(pool._conns) == 0

