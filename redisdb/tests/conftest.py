# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import time

import pytest
import redis

from .common import PORT, PASSWORD, REPLICA_PORT, MASTER_PORT


HERE = os.path.abspath(os.path.dirname(__file__))


def wait_for_cluster(conn):
    """
    Wait for the slave to connect to the master
    """
    attempts = 0
    while True:
        if attempts > 5:
            return False

        try:
            if conn.ping() and conn.info().get('connected_slaves'):
                return True
        except redis.ConnectionError:
            attempts += 1
            time.sleep(1)


@pytest.fixture(scope="session")
def redis_auth():
    """
    Start a standalone redis server requiring authentication before running a
    test and stop it afterwards.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    env = os.environ
    env['REDIS_CONFIG'] = os.path.join(HERE, 'config', 'auth.conf')
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', 'standalone.compose')
    ]

    subprocess.check_call(args + ["up", "-d"], env=env)
    yield
    subprocess.check_call(args + ["down"], env=env)


@pytest.fixture(scope="session")
def redis_cluster():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'compose', '1m-2s.compose')
    ]

    subprocess.check_call(args + ["up", "-d"])
    # wait for the cluster to be up before yielding
    wait_for_cluster(redis.Redis(port=MASTER_PORT, db=14))
    yield
    subprocess.check_call(args + ["down"])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def redis_instance():
    return {
        'host': 'localhost',
        'port': PORT,
        'password': PASSWORD,
        'tags': ["foo:bar"]
    }


@pytest.fixture
def replica_instance():
    return {
        'host': 'localhost',
        'port': REPLICA_PORT,
        'tags': ["bar:baz"]
    }


@pytest.fixture
def master_instance():
    return {
        'host': 'localhost',
        'port': MASTER_PORT,
    }
