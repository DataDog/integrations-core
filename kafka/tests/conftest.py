# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.utils import load_jmx_config

from .common import COMPOSE_FILE, HERE, IS_KRAFT


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', COMPOSE_FILE)

    if IS_KRAFT:
        log_pattern = r'\[KafkaRaftServer nodeId=\d+\] Kafka Server started'
    else:
        log_pattern = r'\[KafkaServer id=\d+\] started'

    with docker_run(
        compose_file,
        conditions=[
            CheckDockerLogs(
                compose_file,
                [log_pattern],
                matches="all",
                service="kafka",
            ),
        ],
        waith_for_health=True,
    ):
        yield load_jmx_config(), {'use_jmx': True}
