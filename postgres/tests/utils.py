# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import psycopg2
import pytest

from .common import POSTGRES_VERSION

requires_over_10 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 10,
    reason='This test is for over 10 only (make sure POSTGRES_VERSION is set)',
)
requires_over_14 = pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 14,
    reason='This test is for over 14 only (make sure POSTGRES_VERSION is set)',
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
