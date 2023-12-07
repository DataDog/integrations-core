# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time

import psycopg2
import pytest

from .common import PASSWORD_ADMIN, POSTGRES_VERSION, USER_ADMIN

requires_over_10 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 10,
    reason='This test is for over 10 only (make sure POSTGRES_VERSION is set)',
)
requires_over_11 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 11,
    reason='This test is for over 11 only (make sure POSTGRES_VERSION is set)',
)
requires_over_12 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 12,
    reason='This test is for over 12 only (make sure POSTGRES_VERSION is set)',
)
requires_over_13 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 13,
    reason='This test is for over 13 only (make sure POSTGRES_VERSION is set)',
)
requires_over_14 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 14,
    reason='This test is for over 14 only (make sure POSTGRES_VERSION is set)',
)
requires_over_15 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 15,
    reason='This test is for over 15 only (make sure POSTGRES_VERSION is set)',
)


def _get_conn(db_instance, dbname=None, user=None, password=None, application_name='test'):
    conn = psycopg2.connect(
        host=db_instance['host'],
        port=db_instance['port'],
        dbname=dbname or db_instance['dbname'],
        user=user or db_instance['username'],
        password=password or db_instance['password'],
        application_name=application_name,
    )
    conn.autocommit = True
    return conn


# Get a connection with superuser
def _get_superconn(db_instance, application_name='test'):
    return _get_conn(db_instance, user=USER_ADMIN, password=PASSWORD_ADMIN, application_name=application_name)


def lock_table(pg_instance, table, lock_mode):
    lock_conn = _get_superconn(pg_instance)
    cur = lock_conn.cursor()
    cur.execute('BEGIN')
    cur.execute(f'lock {table} IN {lock_mode} MODE')
    return lock_conn


def kill_vacuum(pg_instance):
    with _get_superconn(pg_instance) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE query ~* '^vacuum'")


# Wait until the query yielding a single value cross the provided threshold
def _wait_for_value(db_instance, lower_threshold, query, attempts=10):
    value = 0
    current_attempt = 0
    # Stats table behave slightly differently than normal tables
    # Repeating the same query within a transaction will yield the
    # same value, despite the fact that the transaction is in READ COMMITED
    # To avoid this, we avoid transaction block created by the with statement
    conn = _get_superconn(db_instance)
    while value <= lower_threshold and current_attempt < attempts:
        with conn.cursor() as cur:
            cur.execute(query)
            value = cur.fetchall()[0][0]
            time.sleep(0.1)
            current_attempt += 1
    conn.close()


def run_vacuum_thread(pg_instance, vacuum_query, application_name='test'):
    def run_analyze():
        conn_vacuum = _get_superconn(pg_instance, application_name)
        with conn_vacuum.cursor() as cur:
            cur.execute("set statement_timeout='2s'")
            cur.execute('set vacuum_cost_delay=100')
            cur.execute('set vacuum_cost_limit=1')
            try:
                cur.execute(vacuum_query)
            except psycopg2.errors.QueryCanceled:
                pass
        conn_vacuum.close()

    # Start vacuum
    thread = threading.Thread(target=run_analyze)
    thread.start()
    return thread


def run_one_check(check, db_instance, cancel=True):
    """
    Run check and immediately cancel.
    Waits for all threads to close before continuing.
    """
    check.check(db_instance)
    if cancel:
        check.cancel()
    if check.statement_samples._job_loop_future is not None:
        check.statement_samples._job_loop_future.result()
    if check.statement_metrics._job_loop_future is not None:
        check.statement_metrics._job_loop_future.result()
    if check.metadata_samples._job_loop_future is not None:
        check.metadata_samples._job_loop_future.result()
