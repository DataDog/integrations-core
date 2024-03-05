# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import select
import time

import psycopg2
import pytest
from flaky import flaky

from .common import DB_NAME, HOST, POSTGRES_VERSION, _get_expected_tags


def wait_on_result(cursor=None, sql=None, binds=None, expected_value=None):
    for _i in range(300):
        cursor.execute(sql, binds)
        result = cursor.fetchone()[0]
        if result == expected_value:
            break

        time.sleep(0.1)
    else:
        return False

    return True


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 9.2,
    reason='Deadlock test requires version 9.2 or higher (make sure POSTGRES_VERSION is set)',
)
@flaky(max_runs=5)
def test_deadlock(aggregator, dd_run_check, integration_check, pg_instance):
    '''
    This test creates a deadlock by having two connections update the same two rows in opposite order.
    conn1 - open new transaction (implicitly), update row 1, do not commit (transaction left open)
    conn2 - open new transaction (explicitly), update row 2, update row 1, (attempt to) commit
    conn1 - update row 2, (attempt to) commit
    conn2 is blocked waiting for conn1 to update row 1
    conn1 is blocked waiting for conn2 to update row 2
    deadlock occurs
    '''
    check = integration_check(pg_instance)
    check._connect()
    conn = check._new_connection(pg_instance['dbname'])
    cursor = conn.cursor()

    def wait(conn):
        while True:
            state = conn.poll()
            if state == psycopg2.extensions.POLL_OK:
                break
            elif state == psycopg2.extensions.POLL_WRITE:
                select.select([], [conn.fileno()], [])
            elif state == psycopg2.extensions.POLL_READ:
                select.select([conn.fileno()], [], [])
            else:
                raise psycopg2.OperationalError("poll() returned %s" % state)
            time.sleep(0.1)

    conn_args = {'host': HOST, 'dbname': DB_NAME, 'user': "bob", 'password': "bob"}
    conn_args_async = copy.copy(conn_args)
    conn_args_async["async_"] = 1
    conn1 = psycopg2.connect(**conn_args)
    conn1.autocommit = False

    conn2 = psycopg2.connect(**conn_args_async)
    wait(conn2)

    appname = 'deadlock sess'
    appname1 = appname + '1'
    appname2 = appname + '2'
    appname_sql = "SET application_name=%s"
    update_sql = "update personsdup1 set address = 'changed' where personid = %s"

    deadlock_count_sql = "select deadlocks from pg_stat_database where datname = %s"
    cursor.execute(deadlock_count_sql, (DB_NAME,))
    deadlocks_before = cursor.fetchone()[0]

    cur1 = conn1.cursor()
    cur1.execute(appname_sql, (appname1,))
    cur1.execute(update_sql, (1,))

    cur2 = conn2.cursor()
    cur2.execute(
        """SET application_name=%s;
begin transaction;
{};
{};
commit;
""".format(
            update_sql, update_sql
        ),
        (appname2, 2, 1),
    )

    lock_count_sql = """SELECT COUNT(1)
   FROM  pg_catalog.pg_locks         blocked_locks
    JOIN pg_catalog.pg_stat_activity blocked_activity  ON blocked_activity.pid = blocked_locks.pid
    JOIN pg_catalog.pg_locks         blocking_locks
        ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
        AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
        AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
        AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
        AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
        AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
        AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
        AND blocking_locks.pid != blocked_locks.pid
    JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
   WHERE NOT blocked_locks.GRANTED
    AND blocking_activity.application_name = %s
    AND blocked_activity.application_name = %s """

    is_locked = wait_on_result(cursor=cursor, sql=lock_count_sql, binds=(appname1, appname2), expected_value=1)

    if not is_locked:
        raise Exception("ERROR: Couldn't reproduce a deadlock. That can happen on an extremely overloaded system.")

    try:
        cur1.execute(update_sql, (2,))
        cur1.execute("commit")
    except psycopg2.errors.DeadlockDetected:
        pass

    conn1.close()
    conn2.close()

    dd_run_check(check)

    wait_on_result(cursor=cursor, sql=deadlock_count_sql, binds=(DB_NAME,), expected_value=deadlocks_before + 1)

    aggregator.assert_metric(
        'postgresql.deadlocks.count',
        value=deadlocks_before + 1,
        tags=_get_expected_tags(check, pg_instance, db=pg_instance["dbname"]),
    )

    conn.close()
