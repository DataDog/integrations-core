# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import threading
import time

import psycopg
import pytest

from datadog_checks.base import AgentCheck

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
requires_over_16 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 16,
    reason='This test is for over 16 only (make sure POSTGRES_VERSION is set)',
)
requires_under_17 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) >= 17,
    reason='This test is for under 17 only (make sure POSTGRES_VERSION is set)',
)
requires_over_17 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 17,
    reason='This test is for over 17 only (make sure POSTGRES_VERSION is set)',
)


def _get_conn(db_instance, dbname=None, user=None, password=None, application_name='test', autocommit=True):
    conn = psycopg.connect(
        host=db_instance['host'],
        port=db_instance['port'],
        dbname=dbname or db_instance['dbname'],
        user=user or db_instance['username'],
        password=password or db_instance['password'],
        application_name=application_name,
        autocommit=autocommit,
    )
    return conn


# Get a connection with superuser
def _get_superconn(db_instance, application_name='test', autocommit=True):
    return _get_conn(
        db_instance, user=USER_ADMIN, password=PASSWORD_ADMIN, application_name=application_name, autocommit=autocommit
    )


def lock_table(pg_instance, table, lock_mode, application_name='test'):
    lock_conn = _get_superconn(pg_instance, application_name)
    cur = lock_conn.cursor()
    cur.execute('BEGIN')
    cur.execute(f'lock {table} IN {lock_mode} MODE')
    return lock_conn


def kill_session(pg_instance, query_pattern, application_name='test'):
    with _get_superconn(pg_instance, application_name) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT pg_cancel_backend(pid)
FROM pg_stat_activity
WHERE query ~* '{query_pattern}' AND pid!=pg_backend_pid()"""
            )


def kill_vacuum(pg_instance, application_name='test'):
    kill_session(pg_instance, '^vacuum', application_name)


# Wait until the query yielding a single value cross the provided threshold
def _wait_for_value(db_instance, lower_threshold, query, attempts=10, application_name='test'):
    value = 0
    current_attempt = 0
    # Stats table behave slightly differently than normal tables
    # Repeating the same query within a transaction will yield the
    # same value, despite the fact that the transaction is in READ COMMITED
    # To avoid this, we avoid transaction block created by the with statement
    conn = _get_superconn(db_instance, application_name)
    while value <= lower_threshold and current_attempt < attempts:
        with conn.cursor() as cur:
            cur.execute(query)
            value = cur.fetchall()[0][0]
            time.sleep(0.1)
            current_attempt += 1
    conn.close()


def run_query_thread(pg_instance, query, application_name='test', init_statements=None):
    def run_query():
        conn = _get_superconn(pg_instance, application_name)
        with conn.cursor() as cur:
            if init_statements:
                for stmt in init_statements:
                    cur.execute(stmt)
            try:
                cur.execute(query)
            except psycopg.errors.QueryCanceled:
                pass
        conn.close()

    # Start thread
    thread = threading.Thread(target=run_query)
    thread.start()
    return thread


def run_vacuum_thread(pg_instance, vacuum_query, application_name='test'):
    init_stmts = ["set statement_timeout='2s'", 'set vacuum_cost_delay=100', 'set vacuum_cost_limit=1']
    return run_query_thread(pg_instance, vacuum_query, application_name, init_stmts)


def run_one_check(check: AgentCheck, cancel=True):
    """
    Run check and immediately cancel.
    Waits for all threads to close before continuing.
    """
    check.run()
    if cancel:
        check.cancel()
    if check.statement_samples._job_loop_future is not None:
        check.statement_samples._job_loop_future.result()
    if check.statement_metrics._job_loop_future is not None:
        check.statement_metrics._job_loop_future.result()
    if check.metadata_samples._job_loop_future is not None:
        check.metadata_samples._job_loop_future.result()


def normalize_object(obj):
    if isinstance(obj, dict):
        return {k: normalize_object(v) for k, v in obj.items()}
    if isinstance(obj, list):
        normalized = [normalize_object(item) for item in obj]
        return sorted(normalized, key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(obj, tuple):
        return tuple(normalize_object(item) for item in obj)
    return obj


# WaitGroup is used like go's sync.WaitGroup
class WaitGroup(object):
    def __init__(self):
        self.count = 0
        self.cv = threading.Condition()

    def add(self, n):
        self.cv.acquire()
        self.count += n
        self.cv.release()

    def done(self):
        self.cv.acquire()
        self.count -= 1
        if self.count == 0:
            self.cv.notify_all()
        self.cv.release()

    def wait(self):
        self.cv.acquire()
        while self.count > 0:
            self.cv.wait()
        self.cv.release()
