# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from .common import CHECK_CONFIG, HERE


@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        conditions=[
            # Kafka Broker
            CheckDockerLogs('broker', 'Monitored service is now ready'),
            # Kafka Schema Registry
            CheckDockerLogs('schema-registry', 'Server started, listening for requests...', attempts=90,),
            # Kafka Connect
            CheckDockerLogs('connect', 'Kafka Connect started', attempts=120),
        ],
    ):
        yield CHECK_CONFIG, {'use_jmx': True}
