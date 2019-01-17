# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import os

from datadog_checks.dev import docker_run
from datadog_checks.snmp import SnmpCheck

from .common import SNMP_CONF

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_DIR = os.path.join(HERE, 'compose')


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
        yield SNMP_CONF


@pytest.fixture
def check():
    return SnmpCheck('snmp', {}, {}, {})
