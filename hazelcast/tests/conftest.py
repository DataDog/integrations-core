# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
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
            CheckDockerLogs('hazelcast_management_center', [r'Members \[']),
            CheckDockerLogs('hazelcast2', [r'Members \{size:']),
        ],
        sleep=10,
    ):
        config = load_jmx_config()
        config['instances'] = [common.INSTANCE_MEMBER_JMX, common.INSTANCE_MC_JMX, common.INSTANCE_MC_PYTHON]
        yield config, {'use_jmx': True}


@pytest.fixture(scope='session')
def hazelcast_check():
    return lambda instance: HazelcastCheck('hazelcast', {}, [instance])
