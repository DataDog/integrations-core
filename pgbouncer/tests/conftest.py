# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function
import subprocess
import os
import time

import pytest
import psycopg2

from . import common

HERE = os.path.dirname(os.path.abspath(__file__))


def wait_for(service_name, port):
    """
    Try to connect to postgres/pgbouncer
    """
    for _ in range(10):
        try:
            psycopg2.connect(host=common.HOST, port=port, user=common.USER, password=common.PASS,
                             database=common.DB, connect_timeout=2)
            print("{} started".format(service_name))
            return True
        except Exception:
            print("Waiting for {}...".format(service_name))
            time.sleep(1)

    return False


@pytest.fixture(scope="session", autouse=True)
def pgb_service():
    """
    Start postgres and install pgbouncer. If there's any problem executing
    docker-compose, let the exception bubble up.
    """
    env = os.environ
    env['TEST_RESOURCES_PATH'] = os.path.join(HERE, 'resources')
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'docker-compose.yml')
    ]

    subprocess.check_call(args + ["up", "-d"], env=env)

    if not wait_for("Postgres", '5432'):
        subprocess.check_call(args + ["logs"], env=env)
        subprocess.check_call(args + ["down"])
        raise Exception("Postgres boot timed out!")

    if not wait_for("PgBouncer", common.PORT):
        subprocess.check_call(args + ["logs"], env=env)
        subprocess.check_call(args + ["down"])
        raise Exception("PgBouncer boot timed out!")

    yield

    subprocess.check_call(args + ["down"])


@pytest.fixture
def instance():
    return {
        'host': common.HOST,
        'port': common.PORT,
        'username': common.USER,
        'password': common.PASS,
        'tags': ['optional:tag1']
    }


@pytest.fixture
def instance_with_url():
    return {
        'database_url': 'postgresql://datadog:datadog@localhost:16432/datadog_test',
        'tags': ['optional:tag1']
    }


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator
