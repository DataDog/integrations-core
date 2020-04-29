# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
from jmxquery import JMXConnection, JMXQuery

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
            WaitFor(jmx_metrics_ready),
        ],
    ):
        config = load_jmx_config()
        config['instances'] = [common.INSTANCE_MEMBER_JMX, common.INSTANCE_MC_JMX, common.INSTANCE_MC_PYTHON]
        yield config, {'use_jmx': True}


def jmx_metrics_ready():
    jmx_connection = JMXConnection("service:jmx:rmi:///jndi/rmi://{}:{}/jmxrmi".format(common.HOST, common.MEMBER_PORT))
    jmx_query = [JMXQuery('com.hazelcast:type=Metrics,*/bytesRead')]
    metrics = jmx_connection.query(jmx_query)
    assert len(metrics) >= 0


@pytest.fixture(scope='session')
def hazelcast_check():
    return lambda instance: HazelcastCheck('hazelcast', {}, [instance])
