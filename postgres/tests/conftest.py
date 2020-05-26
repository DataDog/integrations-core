# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os

import psycopg2
import pytest
from semver import VersionInfo

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.postgres import PostgreSql

from .common import DB_NAME, HOST, PASSWORD, PORT, USER

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE = {'host': HOST, 'port': PORT, 'username': USER, 'password': PASSWORD, 'dbname': DB_NAME, 'tags': ['foo:bar']}


def connect_to_pg():
    psycopg2.connect(host=HOST, dbname=DB_NAME, user=USER, password=PASSWORD)


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    """
    Start a standalone postgres server requiring authentication.
    """
    with docker_run(os.path.join(HERE, 'compose', 'docker-compose.yaml'), conditions=[WaitFor(connect_to_pg)]):
        yield e2e_instance


@pytest.fixture
def check():
    c = PostgreSql('postgres', {}, [{'dbname': 'dbname', 'host': 'localhost', 'port': '5432'}])
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
    return copy.deepcopy(INSTANCE)
