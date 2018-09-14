# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import sys
import time
import pytest
from datadog_checks.dev import docker_run, RetryError
from datadog_checks.utils.common import get_docker_hostname
from datadog_checks.zk import ZookeeperCheck
from datadog_checks.zk.zk import ZKConnectionFailure


CHECK_NAME = 'zk'
HOST = get_docker_hostname()
PORT = 12181
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)

STAT_METRICS = [
    'zookeeper.latency.min',
    'zookeeper.latency.avg',
    'zookeeper.latency.max',
    'zookeeper.bytes_received',
    'zookeeper.bytes_sent',
    'zookeeper.connections',
    'zookeeper.connections',
    'zookeeper.bytes_outstanding',
    'zookeeper.outstanding_requests',
    'zookeeper.zxid.epoch',
    'zookeeper.zxid.count',
    'zookeeper.nodes',
    'zookeeper.instances',
    'zookeeper.packets.received',
    'zookeeper.packets.sent'
]

MNTR_METRICS = [
    'zookeeper.packets_sent',
    'zookeeper.approximate_data_size',
    'zookeeper.num_alive_connections',
    'zookeeper.open_file_descriptor_count',
    'zookeeper.avg_latency',
    'zookeeper.znode_count',
    'zookeeper.outstanding_requests',
    'zookeeper.min_latency',
    'zookeeper.ephemerals_count',
    'zookeeper.watch_count',
    'zookeeper.max_file_descriptor_count',
    'zookeeper.packets_received',
    'zookeeper.max_latency',
]

STATUS_TYPES = [
    'leader',
    'follower',
    'observer',
    'standalone',
    'down',
    'inactive',
    'unknown',
]


@pytest.fixture
def get_instance():
    return {
        'host': HOST,
        'port': PORT,
        'expected_mode': "standalone",
        'tags': ["mytag"]
    }


@pytest.fixture
def get_invalid_mode_instance():
    return {
        'host': HOST,
        'port': PORT,
        'expected_mode': "follower",
        'tags': []
    }


@pytest.fixture
def get_conn_failure_config():
    return {
        'host': HOST,
        'port': 2182,
        'expected_mode': "down",
        'tags': []
    }


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def get_version():
    zk_version = os.environ.get("ZK_VERSION")
    version = [int(k) for k in zk_version.split(".")]
    if len(version) == 2:
        version += [0]
    return version


@pytest.fixture(scope="session")
def spin_up_zk():
    def condition():
        sys.stderr.write("Waiting for ZK to boot...\n")
        booted = False
        for _ in xrange(10):
            try:
                out = ZookeeperCheck._send_command('ruok', HOST, PORT, 500)
                out.seek(0)
                if out.readline() != 'imok':
                    raise ZKConnectionFailure()
                booted = True
                break
            except ZKConnectionFailure:
                time.sleep(1)

        if not booted:
            raise RetryError("Zookeeper failed to boot!")
        sys.stderr.write("ZK boot complete.\n")

    compose_file = os.path.join(HERE, 'compose', 'zk.yaml')
    if get_version() >= [3, 5, 0]:
        compose_file = os.path.join(HERE, 'compose', 'zk35plus.yaml')

    with docker_run(compose_file, conditions=[condition]):
        yield
