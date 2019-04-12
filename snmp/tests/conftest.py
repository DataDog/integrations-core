# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.snmp import SnmpCheck

from .common import COMPOSE_DIR, SCALAR_OBJECTS, SCALAR_OBJECTS_WITH_TAGS, TABULAR_OBJECTS, generate_instance_config


@pytest.fixture(scope='session')
def dd_environment():
    env = {'COMPOSE_DIR': COMPOSE_DIR}
    with docker_run(os.path.join(COMPOSE_DIR, 'docker-compose.yaml'), env_vars=env, log_patterns="Listening at"):
        yield generate_instance_config(SCALAR_OBJECTS + SCALAR_OBJECTS_WITH_TAGS + TABULAR_OBJECTS)


@pytest.fixture
def check():
    return SnmpCheck('snmp', {}, {}, {})
