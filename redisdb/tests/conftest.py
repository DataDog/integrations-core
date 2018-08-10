# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import time

import pytest
import redis

from datadog_checks.dev import LazyFunction, RetryError, docker_run
from .common import HOST, PORT, MASTER_PORT, REPLICA_PORT, PASSWORD


HERE = os.path.dirname(os.path.abspath(__file__))


class CheckCluster(LazyFunction):
    def __init__(self, master_data, replica_data, attempts=60, wait=1):
        self.master_data = master_data
        self.replica_data = replica_data
        self.attempts = attempts
        self.wait = wait

    def __call__(self):
        """Wait for the slave to connect to the master"""
        master = redis.Redis(**self.master_data)
        replica = redis.Redis(**self.replica_data)

        for _ in range(self.attempts):
            try:
                if (
                    master.ping()
                    and replica.ping()
                    and master.info().get('connected_slaves')
                    and replica.info().get('master_link_status') != 'down'
                ):
                    break
            except redis.ConnectionError:
                pass

            time.sleep(self.wait)
        else:
            raise RetryError(
                'Redis cluster boot timed out!\n'
                'Master: {}\n'
                'Replica: {}'.format(
                    master,
                    replica
                )
            )


@pytest.fixture(scope='session')
def redis_auth():
    """
    Start a standalone redis server requiring authentication before running a
    test and stop it afterwards.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    with docker_run(
        os.path.join(HERE, 'compose', 'standalone.compose'),
        env_vars={'REDIS_CONFIG': os.path.join(HERE, 'config', 'auth.conf')}
    ):
        yield


@pytest.fixture(scope='session')
def redis_cluster():
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """
    with docker_run(
        os.path.join(HERE, 'compose', '1m-2s.compose'),
        conditions=[
            CheckCluster(
                {'port': MASTER_PORT, 'db': 14, 'host': HOST},
                {'port': REPLICA_PORT, 'db': 14, 'host': HOST},
            )
        ]
    ):
        yield


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
        'keys': ['test_*'],
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
