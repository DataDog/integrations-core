# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time

import psycopg
import pytest

from .common import POSTGRES_VERSION

requires_over_10 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 10,
    reason='This test is for over 10 only (make sure POSTGRES_VERSION is set)',
)
requires_over_11 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 11,
    reason='This test is for over 11 only (make sure POSTGRES_VERSION is set)',
)
requires_over_13 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 13,
    reason='This test is for over 13 only (make sure POSTGRES_VERSION is set)',
)
requires_over_14 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 14,
    reason='This test is for over 14 only (make sure POSTGRES_VERSION is set)',
)


def _get_conn(db_instance, dbname=None, user=None, password=None, application_name='test'):
    conn = psycopg.connect(
        host=db_instance['host'],
        port=db_instance['port'],
        dbname=dbname or db_instance['dbname'],
        user=user or db_instance['username'],
        password=password or db_instance['password'],
        application_name=application_name,
        autocommit=True,
    )
    return conn


# Get a connection with superuser
def _get_superconn(db_instance, application_name='test'):
    return _get_conn(db_instance, user='postgres', password='datad0g', application_name=application_name)


# Wait until the query yielding a single value cross the provided threshold
def _wait_for_value(db_instance, lower_threshold, query):
    value = 0
    with _get_superconn(db_instance) as conn:
        with conn.cursor() as cur:
            while value <= lower_threshold:
                cur.execute(query)
                value = cur.fetchall()[0][0]
            time.sleep(0.1)


def run_one_check(check, db_instance):
    """
    Run check and immediately cancel.
    Waits for all threads to close before continuing.
    """
    check.check(db_instance)
    check.cancel()


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
