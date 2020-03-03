# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.utils import load_jmx_config

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        build=True,
        mount_logs=True,
        conditions=[
            CheckDockerLogs(
                compose_file,
                [
                    # Management Center
                    'Hazelcast Management Center successfully started',
                    r'Members \[2',
                    # Members connected to each other
                    r'Members \{size:2',
                ],
                matches='all',
            )
        ],
    ):
        config = load_jmx_config()
        config['instances'] = [
            {'host': common.HOST, 'port': common.MEMBER_PORT, 'is_jmx': True},
            {'host': common.HOST, 'port': common.MC_PORT, 'is_jmx': True},
            {'mc_health_check_endpoint': common.MC_HEALTH_CHECK_ENDPOINT},
        ]
        yield config, {'use_jmx': True}
