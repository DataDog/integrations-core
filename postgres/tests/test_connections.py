# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime
import time

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

    db = pool.get_connection('postgres', 999 * 1000)
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
    ttl_long = 90 * 1000
    ttl_short = 1

    def get_time():
        with pool.get_connection('postgres', 1).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT now()")
            return cursor.fetchone()

    def get_activity():
        with pool.get_connection('postgres', 1).cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(
                "SELECT pid, datname, usename, state, query_start, state_change FROM pg_stat_activity "
                "WHERE usename = 'datadog' AND datname LIKE 'dogs%%' AND query_start > %s",
                start_time,
            )
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
            assert (
                approximate_deadline - datetime.timedelta(seconds=1)
                < deadline
                < approximate_deadline + datetime.timedelta(seconds=1)
            )
            assert not db.closed
            assert db.status == psycopg2.extensions.STATUS_READY
        # Check that those pooled connections do exist on the database
        rows = get_activity()
        assert len(rows) == 50
        assert len(set(row['datname'] for row in rows)) == 50
        assert all(row['state'] == 'idle' for row in rows)

        # Repeat this process many times and expect that only one connection is created per database
        for _ in range(500):
            get_many_connections(51, ttl_long)

            rows = get_activity()

            attempts_to_verify = 5
            # Loop here to prevent flakiness. Sometimes postgres doesn't immediately terminate backends.
            # The test can be considered successful as long as the backend is eventually terminated.
            for attempt in range(attempts_to_verify):
                server_pids = set(row['pid'] for row in rows)
                conn_pids = set(db.info.backend_pid for db, _ in pool._conns.values())
                leaked_rows = list(row for row in rows if row['pid'] in server_pids - conn_pids)
                if not leaked_rows:
                    break
                if attempt < attempts_to_verify - 1:
                    time.sleep(1)
                    continue
                assert len(leaked_rows) == 0, 'Found leaked rows on the server not in the connection pool'

            assert len(set(row['datname'] for row in rows)) == 51
            assert len(rows) == 51, 'Possible leaked connections'
            assert all(row['state'] == 'idle' for row in rows)

        # Now update db connections with short-lived TTLs and expect them to self-prune
        get_many_connections(55, ttl_short)
        pool.prune_connections()
        attempts_to_verify = 5
        for attempt in range(attempts_to_verify):
            leaked_rows = get_activity()
            if attempt < attempts_to_verify - 1:
                time.sleep(1)
                continue
            assert len(leaked_rows) == 0, 'Found leaked rows remaining after TTL was updated to short TTL'

        # Final check that the server contains no leaked connections still open
        rows = get_activity()
        assert len(rows) == 0

    finally:
        success = pool.close_all_connections()
        print('Successfully closed all connections? {}'.format(success))
        assert success
        assert len(pool._conns) == 0


def test_pg_terminated_connection_is_safe():
    """
    Tests that the connection pool propery handles the case where a connection has been
    terminated by the server (i.e. the client-side state is stale)
    """
    # TODO
    pass
