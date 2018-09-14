# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import time

import pytest
import mock
from datadog_checks.postgres import PostgreSql

from .common import HOST, PORT, USER, PASSWORD, DB_NAME


HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def check():
    check = PostgreSql('postgres', {}, {})
    check._is_9_2_or_above = mock.MagicMock()
    PostgreSql._known_servers = set()  # reset the global state
    return check


@pytest.fixture(scope="session")
def postgres_standalone():
    """
    Start a standalone postgres server requiring authentication before running a
    test and stopping it afterwards.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    env = os.environ
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'standalone.compose')
    ]

    subprocess.check_call(args + ["up", "-d"], env=env)

    # waiting for PG to start
    attempts = 0
    while True:
        if attempts > 10:
            subprocess.check_call(args + ["down"], env=env)
            raise Exception("PostgreSQL boot timed out!")

        output = subprocess.check_output([
            "docker",
            "inspect",
            "--format='{{json .State.Health.Status}}'",
            "compose_postgres_1"])

        # we get a json string output from docker
        if output.strip() == "'\"healthy\"'":
            break
        attempts += 1
        time.sleep(1)

    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def pg_instance():
    return {
        'host': HOST,
        'port': PORT,
        'username': USER,
        'password': PASSWORD,
        'dbname': DB_NAME,
        'use_psycopg2': os.environ.get('USE_PSYCOPG2', "false"),
        'tags': ["foo:bar"]
    }
