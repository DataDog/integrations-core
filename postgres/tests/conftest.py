# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
from collections import deque

import mock
import psycopg2
import pytest
from semver import VersionInfo

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.postgres import PostgreSql

from .common import DB_NAME, HOST, PASSWORD, PORT, POSTGRES_IMAGE, USER

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = {
    'host': HOST,
    'port': PORT,
    'username': USER,
    'password': PASSWORD,
    'dbname': DB_NAME,
    'tags': ['foo:bar'],
    'disable_generic_tags': True,
}


def connect_to_pg():
    psycopg2.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD)


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    """
    Start a standalone postgres server requiring authentication.
    """
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[WaitFor(connect_to_pg)],
        env_vars={"POSTGRES_IMAGE": POSTGRES_IMAGE},
    ):
        yield e2e_instance


@pytest.fixture
def check():
    c = PostgreSql('postgres', {}, [{'dbname': 'dbname', 'host': 'localhost', 'port': '5432', 'username': USER}])
    c._version = VersionInfo(9, 2, 0)
    return c


@pytest.fixture
def integration_check():
    def _check(instance):
        c = PostgreSql('postgres', {}, [instance])
        return c

    return _check


@pytest.fixture
def pg_instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture(scope='session')
def e2e_instance():
    instance = copy.deepcopy(INSTANCE)
    instance['dbm'] = True
    return instance


@pytest.fixture()
def mock_cursor_for_replica_stats():
    with mock.patch('psycopg2.connect') as connect:
        cursor = mock.MagicMock()
        data = deque()
        connect.return_value = mock.MagicMock(cursor=mock.MagicMock(return_value=cursor))

        def cursor_execute(query):
            if "FROM pg_stat_replication" in query:
                data.appendleft(['app1', 'streaming', 'async', '1.1.1.1', 12, 12, 12, 12])
                data.appendleft(['app2', 'backup', 'sync', '1.1.1.1', 13, 13, 13, 13])
            elif query == 'SHOW SERVER_VERSION;':
                data.appendleft(['10.15'])

        def cursor_fetchall():
            while data:
                yield data.pop()

        def cursor_fetchone():
            return data.pop()

        cursor.execute = cursor_execute
        cursor.fetchall = cursor_fetchall
        cursor.fetchone = cursor_fetchone

        yield
