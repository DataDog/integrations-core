# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import time
import os

from datadog_checks.dev import docker_run
from datadog_checks.snmp import SnmpCheck

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_DIR = os.path.join(HERE, 'compose')


@pytest.fixture(scope='session', autouse=True)
def spin_up_snmp():
    env = {
        'COMPOSE_DIR': COMPOSE_DIR
    }
    with docker_run(
        os.path.join(COMPOSE_DIR, 'docker-compose.yaml'),
        env_vars=env
    ):
        time.sleep(5)
        yield


@pytest.fixture
def check():
    return SnmpCheck('snmp', {}, {}, {})
