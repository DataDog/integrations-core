# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import subprocess
import os
import time

import pytest
import redis

import common


def wait_for_consul(master, replica):
    """
    Wait for the slave to connect to the master
    """
    connected = False
    for i in xrange(0, 20):
        try:
            raise Exception('nothing')
        except:
            pass


@pytest.fixture(scope="session")
def spin_up_redis():
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
    master = redis.Redis(port=MASTER_PORT, db=14, host=HOST)
    replica = redis.Redis(port=REPLICA_PORT, db=14, host=HOST)
    if not wait_for_cluster(master, replica):
        raise Exception("Redis cluster boot timed out!")
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
        'host': HOST,
        'port': PORT,
        'password': PASSWORD,
        'tags': ["foo:bar"]
    }


@pytest.fixture
def replica_instance():
    return {
        'host': HOST,
        'port': REPLICA_PORT,
        'tags': ["bar:baz"]
    }


@pytest.fixture
def master_instance():
    return {
        'host': HOST,
        'port': MASTER_PORT,
    }
