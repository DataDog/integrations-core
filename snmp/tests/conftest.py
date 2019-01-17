# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import os

from datadog_checks.dev import docker_run
from datadog_checks.snmp import SnmpCheck

from .common import (
    generate_instance_config, SCALAR_OBJECTS, SCALAR_OBJECTS_WITH_TAGS, TABULAR_OBJECTS, COMPOSE_DIR
)


@pytest.fixture(scope='session', autouse=True)
def dd_environment():
    env = {
        'COMPOSE_DIR': COMPOSE_DIR
    }
    with docker_run(
        os.path.join(COMPOSE_DIR, 'docker-compose.yaml'),
        env_vars=env,
        log_patterns="Listening at"
    ):
        yield generate_instance_config(SCALAR_OBJECTS + SCALAR_OBJECTS_WITH_TAGS + TABULAR_OBJECTS)


@pytest.fixture
def check():
    return SnmpCheck('snmp', {}, {}, {})
