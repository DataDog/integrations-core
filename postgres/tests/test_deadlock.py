# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import threading
import time

import psycopg
import pytest
from psycopg import ClientCursor

from .common import DB_NAME, HOST, PORT, POSTGRES_VERSION


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


@pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 9.2,
    reason='Deadlock test requires version 9.2 or higher (make sure POSTGRES_VERSION is set)',
)
def test_deadlock(aggregator, dd_run_check, integration_check, pg_instance):
    check = integration_check(pg_instance)
    check._connect()
    conn = check._new_connection(pg_instance['dbname'])
    cursor = conn.cursor()

    def execute_in_thread(q, args):
        with psycopg.connect(
            host=HOST, dbname=DB_NAME, user="bob", password="bob", cursor_factory=ClientCursor
        ) as tconn:
            with tconn.cursor() as cur:
                # this will block, and eventually throw when
                # the deadlock is created
                try:
                    cur.execute(q, args)
                except psycopg.errors.DeadlockDetected:
                    pass

    appname = 'deadlock sess'
    appname1 = appname + '1'
    appname2 = appname + '2'
    appname_sql = "SET application_name=%s"
    update_sql = "update personsdup1 set address = 'changed' where personid = %s"

    deadlock_count_sql = "select deadlocks from pg_stat_database where datname = %s"
    cursor.execute(deadlock_count_sql, (DB_NAME,))
    deadlocks_before = cursor.fetchone()[0]

    conn_args = {'host': HOST, 'dbname': DB_NAME, 'user': "bob", 'password': "bob"}
    conn1 = psycopg.connect(**conn_args, autocommit=False, cursor_factory=ClientCursor)

    cur1 = conn1.cursor()
    cur1.execute(appname_sql, (appname1,))
    cur1.execute(update_sql, (1,))

    args = (appname2, 2, 1)
    query = """SET application_name=%s;
begin transaction;
{};
{};
commit;
""".format(
        update_sql, update_sql
    )
    # ... now execute the test query in a separate thread
    lock_task = threading.Thread(target=execute_in_thread, args=(query, args))
    lock_task.start()

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
    except psycopg.errors.DeadlockDetected:
        pass

    dd_run_check(check)

    wait_on_result(cursor=cursor, sql=deadlock_count_sql, binds=(DB_NAME,), expected_value=deadlocks_before + 1)

    aggregator.assert_metric(
        'postgresql.deadlocks.count',
        value=deadlocks_before + 1,
        tags=pg_instance["tags"]
        + [
            "db:{}".format(DB_NAME),
            "port:{}".format(PORT),
            'dd.internal.resource:database_instance:{}'.format(check.resolved_hostname),
        ],
    )
