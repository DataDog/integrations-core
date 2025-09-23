# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from hazelcast import HazelcastClient

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, WaitFor
from datadog_checks.dev.utils import load_jmx_config
from datadog_checks.hazelcast import HazelcastCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        build=True,
        mount_logs=True,
        conditions=[
            CheckDockerLogs('hazelcast_management_center', ['Hazelcast Management Center successfully started']),
            CheckDockerLogs('hazelcast_management_center', ['Started communication with member']),
            CheckDockerLogs('hazelcast2', [r'Hazelcast JMX agent enabled']),
            CheckDockerLogs('hazelcast2', [r'is STARTED']),
            WaitFor(trigger_some_tcp_data),
        ],
        attempts=5,
        attempts_wait=5,
    ):
        config = load_jmx_config()
        config['instances'] = common.INSTANCE_MEMBERS + [common.INSTANCE_MC_JMX, common.INSTANCE_MC_PYTHON]
        yield config, {'use_jmx': True}


def trigger_some_tcp_data():
    # put a bunch data into the cluster so various metrics are initialized
    client = HazelcastClient(
        cluster_name="dev",
        cluster_members=[
            "{}:{}".format(common.HOST, common.MEMBER_REST_PORT),
        ],
    )

    default_map = client.get_map("default_map")
    default_reliable_topic = client.get_reliable_topic("default_reliable_topic")
    default_topic = client.get_topic("default_topic")
    default_queue = client.get_queue("default_queue")

    for i in range(100):
        default_map.put(f"foo{i}", f"bar{i}")
        default_reliable_topic.publish(f"bar{i}")
        default_topic.publish(f"bar{i}")
        default_queue.offer(f"bar{i}")


@pytest.fixture(scope='session')
def hazelcast_check():
    return lambda instance: HazelcastCheck('hazelcast', {}, [instance])
