# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import mock
import psycopg2
import pytest

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.postgres import PostgreSql
from .common import HOST, PORT, USER, PASSWORD, DB_NAME


HERE = os.path.dirname(os.path.abspath(__file__))


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
    c = PostgreSql('postgres', {}, {})
    c._is_9_2_or_above = mock.MagicMock()
    PostgreSql._known_servers = set()  # reset the global state
    return c


@pytest.fixture
def pg_instance():
    return {
        'host': HOST,
        'port': PORT,
        'username': USER,
        'password': PASSWORD,
        'dbname': DB_NAME,
        'use_psycopg2': os.environ.get('USE_PSYCOPG2', 'false'),
        'tags': ['foo:bar'],
    }


@pytest.fixture(scope='session')
def e2e_instance():
    return {
        'host': HOST,
        'port': PORT,
        'username': USER,
        'password': PASSWORD,
        'dbname': DB_NAME,
        'use_psycopg2': os.environ.get('USE_PSYCOPG2', 'true'),
        'tags': ['foo:bar'],
    }
